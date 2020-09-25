# International Trade Data - API Application


The purpose of this project is to download data from the **Monthly International Trade Dataset (MITD)** by using Census API. Census API 
is returned in `JSON` format, but is more user-friendly than many APIs due to its streamlined output in form of a list of lists.

In this project, we'll be downloading 2-digit Harmonized System (HS) data. 
HS is an international classification system administered by the World Customs Organization.

All the code is accompanied with explanations and comments. The final output is a clean dataframe ready for data analysis and/or additional transformations.
One example is offered: monthly data is aggregated to yearly frequency and outputted in `.csv` format. Given the tidy data format, this 
data set is very useful for creating pivot tables as well as dashboards in **Excel**, **Power BI** or any other similar software.


**Note:** To make more than 500 API calls a day, Census API requires users to sign up for an API Key. 
To get one, register [here](http://api.census.gov/data/key_signup.html).


