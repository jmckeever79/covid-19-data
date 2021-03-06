import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime
from uspop import UsPop
from maskstats import MaskStats

class CovidTracker(object):
    uscountyfile = os.path.join(os.pardir, 'us-counties.csv')
    mostrecentdate = None
    df = None
    pop = None
    maskuse = None

    def help(self):
        print('Figure it out for yourself, ass.')

    def load_counties(self):
        if self.df is None:
            self.df = pd.read_csv(self.uscountyfile)
            #self.df = self.df.drop('fips', axis=1)

    def load_population(self):
        if self.pop is None:
            self.pop = UsPop()
            self.pop.load()

    def load_maskstats(self):
        if self.maskuse is None:
            self.maskuse = MaskStats()
            self.maskuse.load()

    def _importpopulation(self, frame):
        return pd.merge(frame, self.pop.df, how='left', left_on=['state', 'county'],
                         right_on=['state', 'county'])

    def _importpopulation_state(self, frame):
        return pd.merge(frame, self.pop.stateframe, how='left', left_on=['state'], right_on=['state'])

    def _importmaskuse(self, frame):
        return pd.merge(frame, self.maskuse.df, how='left', left_on=['fips'], right_on=['COUNTYFP'])

    def _dropfips(self, frame):
        if 'fips' in frame.columns:
            frame = frame.drop('fips', axis=1)
        if 'COUNTYFP' in frame.columns:
            frame = frame.drop('COUNTYFP', axis=1)
        return frame

    def getmostrecentdate(self):
        if self.mostrecentdate is None:
            self.mostrecentdate = self.df['date'].max()
        return self.mostrecentdate

    def getnationaltimeseries(self, stat='cases', **kwargs):
        startdate = kwargs['startdate'] if 'startdate' in kwargs else None
        enddate = kwargs['enddate'] if 'enddate' in kwargs else None
        return self.df.groupby(['date']).sum()[stat].loc[startdate:enddate]

    def _getdateframehelper(self, date):
        return self.df.loc[self.df['date']==date]

    def getdateframe(self, date, indexed=False, includepop=False, includemaskuse=False):
        temp = self._getdateframehelper(date)

        if includepop:
            temp = self._importpopulation(temp)

        if includemaskuse:
            temp = self._importmaskuse(temp)
            
        if indexed:
            temp = temp.set_index(['state', 'county'])

        temp = self._dropfips(temp)

        return temp

    def getstateframe(self, state, group_counties=False, includepop=False):
        temp = self.df.loc[self.df['state']==state]
        if (includepop):
            temp = self._importpopulation(temp)
        groups = ['date']
        if (group_counties):
            groups.append('county')
        temp = temp.groupby(groups).sum()
        return temp

    def getcountyframe(self, state, county):
        temp = self.df.loc[self.df['state']==state].loc[self.df['county']==county]
        temp = temp.groupby(['date']).sum()
        return temp

    def getcounties(self, state):
        sf = self.getstateframe(state)
        return set(sf['county'])

    def _set_index(self, frame):
        return frame.set_index(['state', 'county'])

    def getperiodchange(self, enddate, days=1, **kwargs):
        endframe = self._getdateframehelper(enddate).drop('date', axis=1)
        ts = pd.Timestamp(enddate)
        offset = '1 day' if days==1 else '{0} days'.format(days)
        startdate = str((ts - pd.Timedelta(offset)).date())
        startframe = self._getdateframehelper(startdate).drop('date', axis=1)

        endframe = self._set_index(endframe)
        startframe = self._set_index(startframe)

        pct_change = kwargs['pct_change'] if 'pct_change' in kwargs else False
        cap = kwargs['case_cap'] if 'case_cap' in kwargs else None
        includepop = kwargs['includepop'] if 'includepop' in kwargs else False
        includemaskuse = kwargs['includemaskuse'] if 'includemaskuse' in kwargs else False

        fips = endframe['fips']
        diff = endframe-startframe
        diff['fips'] = fips
        setix = False
        if includepop:
            diff = self._importpopulation(diff)
            setix = True
        if includemaskuse:
            diff = self._importmaskuse(diff)
        if cap:
            diff = diff.where(diff['cases'] >= cap)
        if pct_change:
            diff = diff/startframe
        if setix:
            diff = self._set_index(diff)

        diff = self._dropfips(diff)
        return diff

    def getperiodchange_state(self, state, enddate, days=1, **kwargs):
        temp = self.getperiodchange(enddate, days=days, **kwargs)
        return temp.xs(state, level='state')

    def getperiodchange_county(self, state, county, enddate, days=1, **kwargs):
        return self.getperiodchange_state(state, enddate, days=days, **kwargs).xs(county)

    def getnationaldiffseries(self, stat='cases', **kwargs):
        s = self.getnationaltimeseries(stat=stat, **kwargs)
        return s.diff()

    def getdiffseries(self, stat='cases', startdate=None, enddate=None):
        by_date = self.df.groupby(['date']).sum()[stat].loc[startdate:enddate]
        return by_date.diff()

    def getdiffseries_state(self, state, stat='cases', **kwargs):
        startdate = kwargs['startdate'] if 'startdate' in kwargs else None
        enddate = kwargs['enddate'] if 'enddate' in kwargs else None
        sf = self.getstateframe(state)[stat].loc[startdate:enddate]
        return sf.diff()

    def getdiffseries_county(self, state, county, stat='cases', **kwargs):
        startdate = kwargs['startdate'] if 'startdate' in kwargs else None
        enddate = kwargs['enddate'] if 'enddate' in kwargs else None
        cf = self.getcountyframe(state, county)[stat].loc[startdate:enddate]
        return cf.diff()

    def getdeathspercase(self, date):
        return self._getdeathspercase_helper(self.getdateframe(date))

    def getdeathspercase_state(self, state):
        return self._getdeathspercase_helper(self.getstateframe(state))
    
    def getdeathspercase_county(self, state, county):
        return self._getdeathspercase_helper(self.getcountyframe(state, county))

    def _getdeathspercase_helper(self, df):
        rate = (df['deaths']/df['cases']).rename('deaths per case')
        return pd.concat([df, rate], axis=1, join='inner')

    def _xlabelhelper(self, series):
        return series.index[::int(len(series.index)/4)]

    def plotnation(self, startdate=None, enddate=None, stat='cases'):
        frame = self.getnationaltimeseries(stat=stat, startdate=startdate, enddate=enddate)
        xlabels = self._xlabelhelper(frame)
        plt.plot(frame.index, frame)
        plt.xticks(xlabels, xlabels)
        plt.show()

    def _getstateframe_helper(self, states, stat='cases'):
        if (isinstance(states, str)):
            states = [states]
        result = None
        for state in states:
            state_frame = self.getstateframe(state)[stat].rename(state)
            if (result is None):
                result = state_frame
            else:
                result = pd.concat([result, state_frame], axis=1, join='inner')
        return result

    def plotstate(self, states, startdate=None, enddate=None, stat='cases'):
        frame = self._getstateframe_helper(states, stat).loc[startdate:enddate]
        frame.plot()
        plt.show()

    def _getcountyframe_helper(self, counties, stat='cases'):
        result = None
        for t in counties:
            state = t[0]
            county = t[1]
            name = '{0}, {1}'.format(county, state)
            county_frame = self.getcountyframe(state, county)
            if (county_frame.empty):
                continue
            county_frame = county_frame[stat].rename(name)
            if (result is None):
                result = county_frame
            else:
                result = pd.concat([result, county_frame], axis=1, join='inner')
        return result

    def plotcounty(self, counties, stat='cases'):
        frame = self._getcountyframe_helper(counties, stat)
        frame.plot()
        plt.show()

    def plotdiffseries(self, startdate=None, enddate=None, stat='cases'):
        df = self.getdiffseries(stat=stat).loc[startdate:enddate]
        self._plotbarseries(df)

    def plotdiffseries_state(self, state, startdate=None, enddate=None, stat='cases'):
        df_state = self.getdiffseries_state(state, stat=stat).loc[startdate:enddate]
        self._plotbarseries(df_state)

    def plotdiffseries_county(self, state, county, startdate=None, enddate=None, stat='cases'):
        df_county = self.getdiffseries_county(state, county, stat=stat).loc[startdate:enddate]
        self._plotbarseries(df_county)

    def _plotbarseries(self, series):
        ax = plt.subplot('111')
        b1 = ax.bar(series.index, series.values)
        xlabels = self._xlabelhelper(series)
        plt.xticks(xlabels, xlabels)
        plt.show()

    def plotdiffseriescompare_state(self, state1, state2, startdate=None, enddate=None, stat='cases'):
        df1 = self.getdiffseries_state(state1, stat=stat).rename(state1).loc[startdate:enddate]
        df2 = self.getdiffseries_state(state2, stat=stat).rename(state2)
        joined = pd.concat([df1, df2], axis=1, join='inner')
        self._plotdiffseriescompare(joined)

    def plotdiffseriescompare_county(self, state1, county1, state2, county2, 
                                     startdate=None, enddate=None, stat='cases'):
        df1 = self.getdiffseries_county(state1, county1, stat=stat).rename(county1).loc[startdate:enddate]
        df2 = self.getdiffseries_county(state2, county2, stat=stat).rename(county2)
        joined = pd.concat([df1, df2], axis=1, join='inner')
        self._plotdiffseriescompare(joined)
     
    def _plotdiffseriescompare(self, df):
        ax = plt.subplot('111')
        if (df.columns.size != 2):
            raise Exception('Difference series comparison requires 2 columns')
        col0 = df.columns[0]
        col1 = df.columns[1]
        b1 = ax.bar(df.index, df[col0], align='edge', width=0.4, color='orange')
        b1.set_label(col0)
        b2 = ax.bar(df.index, df[col1], align='edge', width=-0.4, color='blue')
        b2.set_label(col1)
        ax.legend()
        xlabels = df.index[::int(len(df.index)/4)]
        plt.xticks(xlabels, xlabels)
        plt.show()

    def _plotline(self, series):
        plt.plot(series.index, series)
        xlabels = self._xlabelhelper(series)
        plt.xticks(xlabels, xlabels)
        plt.legend()
        plt.show()

    def plotrollingmean(self, window=7, stat='cases', **kwargs):
        frame = self.getnationaldiffseries(stat=stat, **kwargs).rolling(window=window).mean()
        self._plotline(frame)

    def plotrollingmean_state(self, state, window=7, stat='cases', **kwargs):
        frame = self.getdiffseries_state(state, stat=stat, **kwargs).rolling(window=window).mean()
        frame = frame.rename(state)
        self._plotline(frame)

    def plotrollingmean_county(self, state, county, window=7, stat='cases', **kwargs):
        frame = self.getdiffseries_county(state, county, stat=stat, **kwargs).rolling(window=window).mean()
        frame = frame.rename('{0}, {1}'.format(county, state))
        self._plotline(frame)