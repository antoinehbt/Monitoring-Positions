import pandas as pd
import requests
import subprocess
import matplotlib.pyplot as plt
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


################################################ SCRAP

def extract_data():
    # Configure Chrome to run in headless mode among other settings
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")  
    chrome_options.add_argument("--disable-logging")  
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  

    # Initialize the webdriver with the configured options
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Open the page
        driver.get('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
        # Wait for the content to load
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#history-list"))
        )
        # Access the content
        content = element.text
    finally:
        # Close the browser
        driver.quit()

    ################################################ DATA PROCESSING

    # Split the content into lines
    lines = content.strip().split('\n')

    # Group lines by 6
    grouped_lines = [lines[n:n+6] for n in range(0, len(lines), 6)]

    # Create a DataFrame from the groups of lines
    rawdf = pd.DataFrame(grouped_lines, columns=["Product", "Price", "Size", "Leverage", "UPL", "Est. Liq. Price"])

    # Display the DataFrame
    print(rawdf)

    ################################################ REFINED DATA PROCESSING

    # Create a new dataframe
    df = rawdf

    # Function to determine the position based on the first character of "Product"
    def get_position(product):
        return 'LONG' if product.startswith('↑') else 'SHORT'

    # Function to determine the underlying asset based on the last character of "Size"
    def get_underlying_asset(size):
        return 'USDC' if size.endswith('$') else 'ETH'

    # Add the "Position" column using the apply() method
    df['Position'] = df['Product'].apply(get_position)

    # Add the "Underlying Asset" column using the apply() method
    df['Underlying Asset'] = df['Size'].apply(get_underlying_asset)

    # Rearrange the columns so that "Position" and "Underlying Asset" are in 2nd and 3rd position
    columns = df.columns.tolist()
    columns = [columns[0]] + columns[-2:] + columns[1:-2]
    df = df[columns]

    # Retrieve the price of ETH
    def get_ethereum_price():
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd')
        price = response.json().get('ethereum', {}).get('usd')
        return price

    eth_price = get_ethereum_price()

    # Function to convert size and margin to USD
    def convert_to_usd(value, asset):
        # Remove commas from the text
        value = value.replace(",", "")
        if asset == 'USDC':
            # If the asset is in USDC, remove the $ symbol and convert to float
            value = float(value[:-1])
        else:
            # If the asset is in ETH, remove the Ξ symbol and convert to float, then multiply by the ETH price
            value = float(value[:-1]) * eth_price
        return value

    # Apply the processing function to the desired columns
    df.loc[:,'Net Size'] = df.apply(lambda row: convert_to_usd(row['Size'], row['Underlying Asset']), axis=1)
    df.loc[:,'Net UPL'] = df.apply(lambda row: convert_to_usd(row['UPL'], row['Underlying Asset']), axis=1)

    # Rearrange the columns to respect the desired order
    df = df[['Product', 'Position', 'Underlying Asset', 'Price', 'Size', 'Net Size','Leverage', 'UPL', 'Net UPL', 'Est. Liq. Price']]

    # Remove commas and the dollar sign for the column "Est. Liq. Price"
    df["Est. Liq. Price"] = df["Est. Liq. Price"].str.replace(",", "").str.replace("$", "").astype(float)

    # Display the DataFrame
    pd.options.display.float_format = '{:.2f}'.format
    print(df)

    ################################################ EXPORT THE DATAFRAME

    # Export the DataFrame to a CSV file
    df.to_csv('DataPositions.csv', index=False)
    print("DataPosition.csv saved")
    print()

    ################################################ OPEN INTEREST

    # Calculate the open interest with the total sum of the 'Net Size' column
    Open_Interest = df['Net Size'].sum()

    # Filter data where 'Position' is 'SHORT', then calculate the sum of 'Net Size' for these data
    Open_Interest_Short = df.loc[df['Position'] == 'SHORT', 'Net Size'].sum()

    # Filter data where 'Position' is 'LONG', then calculate the sum of 'Net Size' for these data
    Open_Interest_Long = df.loc[df['Position'] == 'LONG', 'Net Size'].sum()

    # Filter data where 'Underlying Asset' is 'ETH', then calculate the sum of 'Net Size' for these data
    Open_Interest_ETH = df.loc[df['Underlying Asset'] == 'ETH', 'Net Size'].sum()
    Open_Interest_Short_ETH = df.loc[(df['Underlying Asset'] == 'ETH') & (df['Position'] == 'SHORT'), 'Net Size'].sum()
    Open_Interest_Long_ETH = df.loc[(df['Underlying Asset'] == 'ETH') & (df['Position'] == 'LONG'), 'Net Size'].sum()

    # Filter data where 'Underlying Asset' is 'USDC', then calculate the sum of 'Net Size' for these data
    Open_Interest_USDC = df.loc[df['Underlying Asset'] == 'USDC', 'Net Size'].sum()
    Open_Interest_Short_USDC = df.loc[(df['Underlying Asset'] == 'USDC') & (df['Position'] == 'SHORT'), 'Net Size'].sum()
    Open_Interest_Long_USDC = df.loc[(df['Underlying Asset'] == 'USDC') & (df['Position'] == 'LONG'), 'Net Size'].sum()

    # Display the results
    # print("Open Interest Metrics")
    # print(f'Total Open Interest: {Open_Interest}')
    # print(f'Total Short Open Interest: {Open_Interest_Short}')
    # print(f'Total Long Open Interest: {Open_Interest_Long}')
    # print(f'Total ETH Open Interest: {Open_Interest_ETH}')
    # print(f'Total USDC Open Interest: {Open_Interest_USDC}')

    # Create a dictionary with descriptions and values
    data_OI = {
        "Description": [
            "Open_Interest",
            "Open_Interest_Short",
            "Open_Interest_Long",
            "Open_Interest_USDC",
            "Open_Interest_ETH",
            "Open_Interest_Short_ETH",
            "Open_Interest_Long_ETH",
            "Open_Interest_Short_USDC",
            "Open_Interest_Long_USDC"
        ],
        "Value": [
            Open_Interest,
            Open_Interest_Short,
            Open_Interest_Long,
            Open_Interest_USDC,
            Open_Interest_ETH,
            Open_Interest_Short_ETH,
            Open_Interest_Long_ETH,
            Open_Interest_Short_USDC,
            Open_Interest_Long_USDC
        ]
    }

    # Create a DataFrame from a dictionary
    summary_df = pd.DataFrame(data_OI)

    summary_df['Percentage (of Open Interest)'] = (summary_df['Value'] / Open_Interest) * 100

    # Print the DataFrame
    pd.options.display.float_format = '{:.2f}'.format
    # print(summary_df)
    print()

################################################ UPL

    # Calculate the total UPL (Unrealized Profit/Loss)
    Total_UPL = df['Net UPL'].sum()

    # Filter data where 'Position' is 'SHORT', then calculate the sum of 'Net UPL' for these data
    Total_UPL_Short = df.loc[df['Position'] == 'SHORT', 'Net UPL'].sum()

    # Filter data where 'Position' is 'LONG', then calculate the sum of 'Net UPL' for these data
    Total_UPL_Long = df.loc[df['Position'] == 'LONG', 'Net UPL'].sum()

    # Filter data where 'Underlying Asset' is 'ETH', then calculate the sum of 'Net UPL' for these data
    Total_UPL_ETH = df.loc[df['Underlying Asset'] == 'ETH', 'Net UPL'].sum()
    Total_UPL_Short_ETH = df.loc[(df['Underlying Asset'] == 'ETH') & (df['Position'] == 'SHORT'), 'Net UPL'].sum()
    Total_UPL_Long_ETH = df.loc[(df['Underlying Asset'] == 'ETH') & (df['Position'] == 'LONG'), 'Net UPL'].sum()

    # Filter data where 'Underlying Asset' is 'USDC', then calculate the sum of 'Net UPL' for these data
    Total_UPL_USDC = df.loc[df['Underlying Asset'] == 'USDC', 'Net UPL'].sum()
    Total_UPL_Short_USDC = df.loc[(df['Underlying Asset'] == 'USDC') & (df['Position'] == 'SHORT'), 'Net UPL'].sum()
    Total_UPL_Long_USDC = df.loc[(df['Underlying Asset'] == 'USDC') & (df['Position'] == 'LONG'), 'Net UPL'].sum()

    # Display the results
    # print(f'Total_UPL: {Total_UPL}')
    # print(f'Total_UPL_Short: {Total_UPL_Short}')
    # print(f'Total_UPL_Long: {Total_UPL_Long}')
    # print(f'Total_UPL_USDC: {Total_UPL_USDC}')
    # print(f'Total_UPL_ETH: {Total_UPL_ETH}')
    # print(f'Total_UPL_Short_ETH: {Total_UPL_Short_ETH}')
    # print(f'Total_UPL_Long_ETH: {Total_UPL_Long_ETH}')
    # print(f'Total_UPL_Short_USDC: {Total_UPL_Short_USDC}')
    # print(f'Total_UPL_Long_USDC: {Total_UPL_Long_USDC}')
    # print()

    # Create a dictionary for UPL data
    data_UPL = {
        "Description": [
            "Total UPL",
            "Total UPL Short",
            "Total UPL Long",
            "Total UPL USDC",
            "Total UPL ETH",
            "Total UPL Short ETH",
            "Total UPL Long ETH",
            "Total UPL Short USDC",
            "Total UPL Long USDC"
        ],
        "Value": [
            Total_UPL,
            Total_UPL_Short,
            Total_UPL_Long,
            Total_UPL_USDC,
            Total_UPL_ETH,
            Total_UPL_Short_ETH,
            Total_UPL_Long_ETH,
            Total_UPL_Short_USDC,
            Total_UPL_Long_USDC
        ]
    }


################################################ LEVERAGE

    # Remove "x" from "Leverage" and convert to float
    df["Leverage"] = df["Leverage"].str.replace("x", "").astype(float)

    # Create a new column "Margin" after "Net Size"
    df.insert(df.columns.get_loc("Net Size") + 1, "Margin", df["Net Size"] / df["Leverage"])

    # Calculate the sum of Margins
    Margin_Sum = df['Margin'].sum()

    # Calculate the average Leverage based on positions
    Leverage_Average = (df['Leverage'] * df['Margin']).sum() / df['Margin'].sum()
    Leverage_Average_Long = (df[df['Position'] == 'LONG']['Leverage'] * df[df['Position'] == 'LONG']['Margin']).sum() / df[df['Position'] == 'LONG']['Margin'].sum()
    Leverage_Average_Short = (df[df['Position'] == 'SHORT']['Leverage'] * df[df['Position'] == 'SHORT']['Margin']).sum() / df[df['Position'] == 'SHORT']['Margin'].sum()
    Leverage_Average_ETH = (df[df['Underlying Asset'] == 'ETH']['Leverage'] * df[df['Underlying Asset'] == 'ETH']['Margin']).sum() / df[df['Underlying Asset'] == 'ETH']['Margin'].sum()
    Leverage_Average_USDC = (df[df['Underlying Asset'] == 'USDC']['Leverage'] * df[df['Underlying Asset'] == 'USDC']['Margin']).sum() / df[df['Underlying Asset'] == 'USDC']['Margin'].sum()

    # Filter the dataframe for various combinations of positions and assets
    Long_ETH = df[(df["Position"] == "LONG") & (df["Underlying Asset"] == "ETH")]
    Short_ETH = df[(df["Position"] == "SHORT") & (df["Underlying Asset"] == "ETH")]
    Long_USDC = df[(df["Position"] == "LONG") & (df["Underlying Asset"] == "USDC")]
    Short_USDC = df[(df["Position"] == "SHORT") & (df["Underlying Asset"] == "USDC")]

    # Calculate the weighted averages for different leverage types
    Leverage_Average_Long_ETH = (Long_ETH["Leverage"] * Long_ETH["Margin"]).sum() / Long_ETH["Margin"].sum()
    Leverage_Average_Short_ETH = (Short_ETH["Leverage"] * Short_ETH["Margin"]).sum() / Short_ETH["Margin"].sum()
    Leverage_Average_Long_USDC = (Long_USDC["Leverage"] * Long_USDC["Margin"]).sum() / Long_USDC["Margin"].sum()
    Leverage_Average_Short_USDC = (Short_USDC["Leverage"] * Short_USDC["Margin"]).sum() / Short_USDC["Margin"].sum()

    # Print statements for displaying leverage metrics
    # print(f'Leverage_Average: {Leverage_Average}')
    # print(f'Leverage_Average_Long: {Leverage_Average_Long}')
    # print(f'Leverage_Average_Short: {Leverage_Average_Short}')
    # print(f'Leverage_Average_ETH: {Leverage_Average_ETH}')
    # print(f'Leverage_Average_USDC: {Leverage_Average_USDC}')
    # print(f'Leverage_Average_Long_ETH: {Leverage_Average_Long_ETH}')
    # print(f'Leverage_Average_Short_ETH: {Leverage_Average_Short_ETH}')
    # print(f'Leverage_Average_Long_USDC: {Leverage_Average_Long_USDC}')
    # print(f'Leverage_Average_Short_USDC: {Leverage_Average_Short_USDC}')
    # print()

    # Create a dictionary for Leverage data
    data_Lev = {
        "Description": [
            "Average Leverage",
            "Average Leverage Short",
            "Average Leverage Long",
            "Average Leverage USDC",
            "Average Leverage ETH",
            "Average Leverage Short ETH",
            "Average Leverage Long ETH",
            "Average Leverage Short USDC",
            "Average Leverage Long USDC"
        ],
        "Value": [
            Leverage_Average,
            Leverage_Average_Long,
            Leverage_Average_Short,
            Leverage_Average_ETH,
            Leverage_Average_USDC,
            Leverage_Average_Short_ETH,
            Leverage_Average_Long_ETH,
            Leverage_Average_Short_USDC,
            Leverage_Average_Long_USDC
        ]
    }

    return data_OI, data_UPL, data_Lev

# Testing the function
data_OI, data_UPL, data_Lev = extract_data()

# print(data_OI)
# print(data_UPL)
# print(data_Lev)

############# PLOT

# Convert dictionaries to dataframes
df1 = pd.DataFrame(data_OI)
df2 = pd.DataFrame(data_UPL)
df3 = pd.DataFrame(data_Lev)

# Assigning specific colors to each bar based on the user's specifications
specified_colors = ['purple', 'purple', 'yellow', 'yellow', 'cyan', 'blue', 'green', 'red', 'grey']

# Keeping the plot order same as originally but inversing the colors to match the user's request
df1['Color'] = specified_colors[::-1]  # Reversing the color order
df2['Color'] = specified_colors[::-1]
df3['Color'] = specified_colors[::-1]

# Adding the value of each bar to the bar chart
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 15))

# Function to add value labels to the bars
def add_value_labels(ax, spacing=5):
    for rect in ax.patches:
        y_value = rect.get_width()
        x_value = rect.get_y() + rect.get_height() / 2

        # Number of points between bar and label
        space = spacing
        va = 'center'

        # If value of bar is negative: Place label left of bar
        if y_value < 0:
            space *= -1
            va = 'center'

        # Use Y value as label and format number
        label = "{:.2f}".format(y_value)

        # Create annotation
        ax.annotate(
            label,                      # Use `label` as label
            (y_value, x_value),         # Place label at end of the bar
            xytext=(space, 0),          # Horizontally shift label by `space`
            textcoords="offset points", # Interpret `xytext` as offset in points
            ha='center',                # Horizontally center label
            va=va)                      # Vertically align label differently for positive and negative values

# Bar chart for dictionary 1 with values
for index, row in df1.iloc[::-1].iterrows():  # Inverting the plot order
    axes[0].barh(row['Description'], row['Value'], color=row['Color'])
add_value_labels(axes[0])
axes[0].set_title('Open Interest Metrics')
axes[0].set_xlabel('Value')
axes[0].set_ylabel('Description')

# Bar chart for dictionary 2 with values
for index, row in df2.iloc[::-1].iterrows():  # Inverting the plot order
    axes[1].barh(row['Description'], row['Value'], color=row['Color'])
add_value_labels(axes[1])
axes[1].set_title('Total UPL Metrics')
axes[1].set_xlabel('Value')
axes[1].set_ylabel('Description')

# Bar chart for dictionary 3 with values
for index, row in df3.iloc[::-1].iterrows():  # Inverting the plot order
    axes[2].barh(row['Description'], row['Value'], color=row['Color'])
add_value_labels(axes[2])
axes[2].set_title('Leverage Average Metrics')
axes[2].set_xlabel('Value')
axes[2].set_ylabel('Description')

plt.tight_layout()
plt.show()