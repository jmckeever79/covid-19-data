import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

class CovidTracker(object):
    repos = 'C:/Users/jj/git/data/covid-19-data'
    uscountyfile = os.path.join(repos, 'us-counties.csv')
    mostrecentdate = None

    def help(self):
        print('Figure it out for yourself, ass.')

    def load_counties(self):
        self.df = pd.read_csv(self.uscountyfile)
        self.df = self.df.drop('fips', axis=1)

    def getmostrecentdate(self):
        if self.mostrecentdate is None:
            self.mostrecentdate = self.df['date'].max()
        return self.mostrecentdate

    def getdateframe(self, date, indexed=False):
        temp = self.df.loc[self.df['date']==date]
        if indexed:
            temp = temp.set_index(['state', 'county'])
        return temp

    def getstateframe(self, state, group_counties=False):
        temp = self.df.loc[self.df['state']==state]
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

    def getperiodchange(self, enddate, days=1, stat='cases', pct_change=False):
        endframe = self.getdateframe(enddate, indexed=False)
        ts = pd.Timestamp(enddate)
        offset = '1 day' if days==1 else '{0} days'.format(days)
        startdate = str((ts - pd.Timedelta(offset)).date())
        startframe = self.getdateframe(startdate, indexed=False)

        endframe = self._set_index(endframe)
        startframe = self._set_index(startframe)

        diff = endframe[stat]-startframe[stat]
        if pct_change:
            diff = diff/startframe[stat]
        return diff

    def getdiffseries(self, stat='cases'):
        by_date = self.df.groupby(['date']).sum()[stat]
        return by_date.diff()

    def getdiffseries_state(self, state, stat='cases'):
        sf = self.getstateframe(state)[stat]
        return sf.diff()

    def getdiffseries_county(self, state, county, stat='cases'):
        cf = self.getcountyframe(state, county)[stat]
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

    def plot_county(self, counties, stat='cases'):
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
        xlabels = series.index[::int(len(series.index)/4)]
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
