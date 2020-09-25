import numpy as np
import pandas as pd
import requests
import time
import copy


# *** PREPARING ITERABLES ***

countries = pd.read_csv('countries.csv', header=None, dtype=object)
# remove the last column, the country abbreviations, since it is not necessary
countries.drop(labels=2, axis=1, inplace=True)
# set column names
country_cols = ['COUNTRY_CODE', 'COUNTRY']
countries.columns = country_cols
# make a dictionary with shorter country name alternatives
updated_country_names = {'Falkland Islands (Islas Malvinas)': 'Falkland Islands',
                         'Denmark, except Greenland': 'Denmark',
                         'Germany (Federal Republic of Germany)': 'Germany',
                         'Moldova (Republic of Moldova)': 'Moldova',
                         'Holy See (Vatican City)': 'Vatican City',
                         'Syria (Syrian Arab Republic)': 'Syria',
                         'Gaza Strip administered by Israel': 'Gaza Strip',
                         'West Bank administered by Israel': 'West Bank',
                         'Yemen (Republic of Yemen)': 'Yemen',
                         'Burma (Myanmar)': 'Myanmar',
                         'Laos (Lao People\'s Democratic Republic)': 'Laos',
                         'North Korea (Democratic People\'s Republic of Korea)': 'North Korea',
                         'South Korea (Republic of Korea)': 'South Korea',
                         'Samoa (Western Samoa)': 'Samoa',
                         'Micronesia, Federated States of': 'Micronesia',
                         'Congo, Republic of the Congo': 'Congo-Brazzaville',
                         'Congo, Democratic Republic of the Congo (formerly Za': 'Congo-Kinshasa',
                         'Tanzania (United Republic of Tanzania)': 'Tanzania',
                         'Christmas Island (in the Indian Ocean)': 'Christmas Island'}
# clean any unwanted whitespace
countries.loc[:,'COUNTRY_CODE'] = countries.loc[:,'COUNTRY_CODE'].str.strip()
countries.loc[:,'COUNTRY'] = countries.loc[:,'COUNTRY'].str.strip()
# replace the long names
countries.loc[:,'COUNTRY'].replace(to_replace=updated_country_names, inplace=True)
# prepare a list of country codes needed for API calls
country_codes = countries.loc[:,'COUNTRY_CODE'].tolist()


districts = pd.read_csv('districts.csv', header=None, dtype=object)
# rename the columns
districts.columns = ['DISTRICT_CODE', 'DISTRICT']
# add the district that's missing on the official district list, but shows up in the data
districts.loc[44] = ['59', 'NORFOLK/MOBILE/CHARLESTON, VA/AL/SC']
# prepare a list of district codes
district_codes = districts.loc[:,'DISTRICT_CODE'].tolist()
# for APIs, divide districts in groups based on the first digit
district_codes_single = districts.loc[:,'DISTRICT_CODE'].str.extract(r'([0-9])').iloc[:,0].unique().tolist()
# save each district group in a separate list
district_groups = []
for group_code in district_codes_single:
    group = districts[districts['DISTRICT_CODE'].str.contains(group_code + r'[0-9]')].loc[:,'DISTRICT_CODE']
    district_groups.append(group.tolist())


# *** MAKING THE API CALLS ***

key = 'c64e82bd341ac24cc8223afd0458afb0f3436c66'  # insert your API key here
# time_interval = '2013-01'
time_interval = 'from+2019-01+to+2019-12'
# Fixed URI parts
exports_endpoint = "https://api.census.gov/data/timeseries/intltrade/exports/hs?get=DISTRICT,E_COMMODITY,ALL_VAL_MO,CNT_VAL_MO,CNT_WGT_MO,AIR_VAL_MO,AIR_WGT_MO,VES_VAL_MO,VES_WGT_MO&COMM_LVL=HS2&key="
imports_endpoint = "https://api.census.gov/data/timeseries/intltrade/imports/hs?get=DISTRICT,I_COMMODITY,GEN_VAL_MO,CNT_VAL_MO,CNT_WGT_MO,AIR_VAL_MO,AIR_WGT_MO,VES_VAL_MO,VES_WGT_MO&COMM_LVL=HS2&key="

# start measuring time elapsed
start = time.time()
# track outcome of each call
quality_control = list()
# save each country's result in a dictionary
countries_data = dict()

for country in country_codes:
    # control variable used to identify the first successful API call for a given country
    status_success = 0
    for district in district_codes_single:
        # build the custom API call
        exp_api = exports_endpoint + key + '&time=' + time_interval + '&CTY_CODE=' + country + '&DISTRICT=' + district + '*'
        imp_api = imports_endpoint + key + '&time=' + time_interval + '&CTY_CODE=' + country + '&DISTRICT=' + district + '*'
        # requesting APIs
        for api in [exp_api, imp_api]:
            api_response = requests.get(api)

            qa = [country, district, 'E' if api == exp_api else 'I', api_response.status_code]
            quality_control.append(qa)

            # manage successful APIs, i.e. status code == 200
            if api_response.status_code == 200:
                status_success += 1
                # save the first successful query result as a dataframe
                if status_success == 1:
                    data = pd.DataFrame(api_response.json())
                    # denote the endpoint
                    data['type'] = 'Exports' if api == exp_api else 'Imports'
                # concatenate subsequent successful query results
                else:
                    data_a = pd.DataFrame(api_response.json())
                    data_a['type'] = 'Exports' if api == exp_api else 'Imports'
                    data = pd.concat([data, data_a.iloc[1:,:]])

            # manage too large requests by iterating through individual districts instead of district groups
            elif api_response.status_code == 500:
                for district_2 in district_groups[int(district)]:
                    if qa[2] == 'E':
                        api_2 = exports_endpoint + key + '&time=' + time_interval + '&CTY_CODE=' + country + '&DISTRICT=' + district_2
                    elif qa[2] == 'I':
                        api_2 = imports_endpoint + key + '&time=' + time_interval + '&CTY_CODE=' + country + '&DISTRICT=' + district_2

                    api_response_2 = requests.get(api_2)
                    qa_2 = [country, district_2, qa[2], api_response_2.status_code]
                    quality_control.append(qa_2)

                    if api_response_2.status_code == 200:
                        status_success += 1
                        if status_success == 1:
                            data = pd.DataFrame(api_response_2.json())
                            # denote the data type
                            data['type'] = 'Exports' if qa[2] == 'E' else 'Imports'
                        # concatenate subsequent successful query results
                        else:
                            data_a = pd.DataFrame(api_response_2.json())
                            data_a['type'] = 'Exports' if qa[2] == 'E' else 'Imports'
                            data = pd.concat([data, data_a.iloc[1:,:]])

    # check if any data was obtained and save data accordingly
    if status_success != 0:
        countries_data[country] = data

    if country_codes[59] == country:
        first_quarter = (time.time()-start)/60
        print('25% completed')
        print('Estimated time remaining: ', round(first_quarter*3, 2), 'minutes')
    elif country_codes[119] == country:
        second_quarter = (time.time()-start)/60
        print('50% completed')
        print('Estimated time remaining: ', round(second_quarter, 2), 'minutes')
    elif country_codes[179] == country:
        third_quarter = (time.time()-start)/60
        print('75% completed')
        print('Estimated time remaining: ', round(third_quarter/3, 2), 'minutes')
    elif country_codes[240] == country:
        print('Complete!\n')

end = time.time()
run_time = end - start


# *** CLEAN_UP FUNCTION ***

# dictionary with preferred replacements for default column names obtained through API
def clean_up(df):
    column_names = {'CTY_CODE': 'COUNTRY_CODE',
                'ALL_VAL_MO': 'VALUE',
                'GEN_VAL_MO': 'VALUE',
                'CNT_VAL_MO': 'CONTAINER_VALUE',
                'CNT_WGT_MO': 'CONTAINER_WEIGHT',
                'AIR_VAL_MO': 'AIR_VALUE',
                'AIR_WGT_MO': 'AIR_WEIGHT',
                'VES_VAL_MO': 'VESSEL_VALUE',
                'VES_WGT_MO': 'VESSEL_WEIGHT',
                'E_COMMODITY': 'COMMODITY_CODE',
                'I_COMMODITY': 'COMMODITY_CODE',
                'DISTRICT': 'DISTRICT_CODE',
                'Imports': 'TYPE',
                'Exports': 'TYPE'}
    # drop the extra district_code column
    df.drop(labels=0, axis=1, inplace=True)
    # replace the default column names (which are now in the first row) with the preferred ones
    df.iloc[0,:].replace(to_replace=column_names, inplace=True)
    # take the first row, convert to upper case, create a list and assign as a header
    df.columns = df.iloc[0].str.upper().tolist()
    # delete the first row
    df.drop(labels=0, inplace=True)
    # drop the rows with total value equal to 0
    df = df[df.loc[:,'VALUE'] != '0'].copy()
    # separate the TIME column into columns YEAR and MONTH
    df[['YEAR','MONTH']] = df['TIME'].str.split("-", expand=True)
    # delete the TIME column
    df.drop(labels='TIME', axis=1, inplace=True)
    # reset index
    df.reset_index(drop=True, inplace=True)
    return df

# call the function to clean the data
for cdf in countries_data:
    countries_data[cdf] = clean_up(countries_data[cdf])

# combine the dataframes
get_the_first_one = 0
concat_start = time.time()

for cdf in countries_data:
    if get_the_first_one == 0:
        get_the_first_one += 1
        final_data = pd.DataFrame(countries_data[cdf])
    elif get_the_first_one == 1:
        final_data = pd.concat([final_data, pd.DataFrame(countries_data[cdf].iloc[1:,:])])

concat_end = time.time()
concat_time = concat_end - concat_start
print('Time needed to combine all the dataframes:', round(concat_time/60, 2), 'minutes\n')

# convert numerical parameters to int
num_params = ['VALUE', 'CONTAINER_VALUE', 'CONTAINER_WEIGHT', 'AIR_VALUE', 'AIR_WEIGHT', 'VESSEL_VALUE', 'VESSEL_WEIGHT']
for param in num_params:
    final_data[param] = pd.to_numeric(final_data[param], errors='coerce')

# check the data info
print(final_data.info())
print()


# *** PERFORMANCE SUMMARY ***

# convert the performance logger to a df
performance = pd.DataFrame(quality_control)
# save call summary to a dictionary
perf_dict = performance.iloc[:,3].value_counts().to_dict()

# number of unresolved failed API calls
trouble = performance[performance.iloc[:,1].str.contains('[0-9][0-9]') & performance.iloc[:,1] == 500].shape[0]
if trouble != 0:
    print('Revision needed!')

# summary
print('API calls made: {:,}'.format(performance.shape[0]))
print('Data download time: ', round(run_time/3600, 2), 'hours')
print('API call breakdown:')
for key in perf_dict:
    print(' '*3, key, ' --> {:>4,}'.format(perf_dict[key]))
print('Unresolved API calls:', trouble)
# print('Total rows downloaded: {:,}'.format(data_raw))
print('Total rows after cleaning: {:,}\n'.format(final_data.shape[0]))


# *** TRANSFORMING AND EXPORTING THE DATA ***

# download clean monthly data
final_data.to_csv('monthly_trade_data_2019.csv')

# several columns are necessary to build a unique identifier in this case
yearly = final_data.groupby(['COUNTRY_CODE', 'COMMODITY_CODE', 'DISTRICT_CODE', 'TYPE', 'YEAR'], as_index=False) \
                      [['VALUE', 'CONTAINER_VALUE', 'CONTAINER_WEIGHT', 'AIR_VALUE', 'AIR_WEIGHT', 'VESSEL_VALUE', 'VESSEL_WEIGHT']].sum()

yearly.to_csv('yearly_trade_data_2019.csv')
