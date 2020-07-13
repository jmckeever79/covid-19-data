from covidtracker import CovidTracker
cd = CovidTracker()
cd.load_counties()
cd.load_population()
df = cd.getperiodchange_state('New York', '2020-07-11', days=7, includepop=True)
#df = cd._imoortpopulation(df)
df.sort_values('cases', ascending=False)
print(df)
