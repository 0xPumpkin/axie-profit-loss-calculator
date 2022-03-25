import web3
from pycoingecko import CoinGeckoAPI
import datetime
from datetime import timedelta, date
import json
import requests
import pandas as pd
import numpy as np
import math
import time
from collections import deque

# FIXED VALUES AND MAPPINGS #

MAX_RESULTS = 100

## REPLACE SAMPLE FILEPATH WITH YOURS; THIS IS WHERE YOUR token_prices.csv FILE IS STORED/WHERE YOUR OUTPUT WILL GO
filepath = r'C:\\Users\\Test\\Test Folder\\'

token_dict = {
	'SLP' : 'smooth-love-potion',
	'AXS' : 'axie-infinity',
	'WETH' : 'ethereum'
}

axie_smart_contracts = {
	'0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5' : 'Ronin WETH Contract',
	'0x97a9107c1793bc407d6f527b77e7fff4d812bece' : 'Axie Infinity Shard Contract',
	'0xa8754b9fa15fc18bb59458815510e40a12cd2014' : 'Smooth Love Potion Contract',
	'0x173a2d4fa585a63acd02c107d57f932be0a71bcc' : 'Axie Egg Coin Contract',
	'0x0b7007c13325c48911f73a2dad5fa5dcbf808adc' : 'USD Coin Contract',
	'0xe514d9deb7966c8be0ca922de8a064264ea6bcd4' : 'Wrapped RON Contract',
	'0x32950db2a7164ae833121501c797d79e7b79d74c' : 'Axie Contract',
	'0x8c811e3c958e190f5ec15fb376533a3398620500' : 'Land Contract',
	'0xa96660f0e4a3e9bc7388925d245a6d4d79e21259' : 'Land Item Contract',
	'0x2da06d60bd413bcbb6586430857433bd9d3a4be4' : 'Exchange Contract',
	'0x213073989821f738a7ba3520c3d31a1f9ad31bbd' : 'Marketplace Contract',
	'0x5b16d12a0c2c88db94115968abd7afa78b6bc504' : 'Offer Auction Contract',
	'0xb255d6a720bb7c39fee173ce22113397119cb930' : 'Katana Factory Contract',
	'0x7d0556d55ca1a92708681e2e231733ebd922597d' : 'Katana Router Contract',
	'0xc6344bc1604fcab1a5aad712d766796e2b7a70b9' : 'AXS-WETH LP Contract',
	'0x306a28279d04a47468ed83d55088d0dcd1369294' : 'SLP-WETH LP Contract',
	'0xa7964991f339668107e2b6a6f6b8e8b74aa9d017' : 'USDC-WETH LP Contract',
	'0x2ecb08f87f075b5769fe543d0e52e40140575ea7' : 'RON-WETH LP Contract',
	'0xe35d62ebe18413d96ca2a2f7cf215bb21a406b4b' : 'Ronin Gateway Contract',
	'0x0000000000000000000000000000000000000011' : 'Ronin Validator Contract',
	'0x05b0bb3c1c320b280501b86706c3551995bc8571' : 'AXS Staking Pool Contract',
	'0x8bd81a19420bad681b7bfc20e703ebd8e253782d' : 'AXS Staking Claim'
}

# ADD YOUR RONIN ADDRESS IN HERE #
ronin_address = 'ronin:0000000000000000000000000000000'
ronin_address = ronin_address.replace('ronin:', '0x')

## READS IN FIXED LIST OF PRICES #
price_df = pd.read_csv(filepath + 'token_prices.csv', delimiter=',', header='infer')

## DEFINE CLASSES AND FUNCTIONS USED IN SCRIPT

### BUY AND SELL QUEUE CLASSES/FUNCTIONS ###
class _Transaction:
	def __init__(self, quantity, price): #add date back in 
		self.quantity = quantity
		self.price = price

class TokenTracker:
	def __init__(self):
		self._token_queue = deque()
		self._total_quantity = 0
		self._total_profit = 0


	def receipt(self, quantity, price):
		if price <= 0:
			raise ValueError("Tokens can't be worth less than 0 USD despite all evidence to the contrary")
		elif quantity <= 0:
			raise ValueError("Can't receive 0 or fewer tokens")
		else:
			self._token_queue.append(_Transaction(quantity, price))
			self._total_quantity += quantity
		return

	def sell(self, quantity, price):
		if price <= 0:
			raise ValueError("Can't pay someone to take the tokens")
		if quantity <=0:
			raise ValueError("Can't sell 0 or fewer tokens")
		if quantity > self._total_quantity:
			raise ValueError("We don't have that much")
		else:
			self._total_quantity -= quantity
			_this_profit = 0
			while quantity > 0:
				if quantity >= self._token_queue[0].quantity:
					profit = (price - self._token_queue[0].price) * self._token_queue[0].quantity
					self._total_profit += profit
					_this_profit += profit
					quantity -= self._token_queue[0].quantity
					self._token_queue.popleft()
				else:
					profit = (price - self._token_queue[0].price) * quantity
					self._total_profit += profit
					_this_profit += profit
					self._token_queue[0].quantity -= quantity
					quantity = 0 
			return _this_profit

	def get_profit(self):
		return self._total_profit

	def get_quantity_on_hand(self):
		return self._total_quantity

### MISCELLANEOUS FUNCTIONS ###
def fix_timestamp(timestamp):
	dt = datetime.datetime.fromtimestamp(timestamp)
	dt = dt.strftime('%d-%m-%Y')
	return dt

def price_lookup(token_name, transaction_date): # NOT CURRENTLY USED BECAUSE OF ISSUES WITH COINGECKO API; IF YOU HAVE AN API KEY THIS WILL WORK BETTER FOR YOU
	try:
		price_history = cg.get_coin_history_by_id(id=token_name, date=transaction_date)
		token_price = price_history['market_data']['current_price']['usd']
		return token_price
	except:
		return 0

def fix_quantities(token_symbol, value):
	if token_symbol == 'WETH':
		return round(int(value) / math.pow(10, 18), 6)
	elif token_symbol == 'AXS':
		return round(int(value) / math.pow(10, 18), 6)
	elif token_symbol == 'SLP':
		return int(value)
	else:
		pass

# DATA PROCESSING #

## INSTANTIATE DATEFRAME
column_names = ['from', 'to', 'value', 'log_index', 'tx_hash', 'block_number', 'timestamp', 'token_address', 'token_decimal', 'token_name', 'token_symbol', 'token_type']
df = pd.DataFrame(columns = column_names)

## RUNS A LIMITED PART OF API PARSING ELEMENT TO GRAB THE TOTAL RESULTS/TO CALCULATE LOOP LENGTH ##
url = "https://explorer.roninchain.com/api/tokentxs?size=1&addr=" + ronin_address
h = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}
response = requests.get(url, headers=h)
json_data = json.loads(response.text)

iter_count = int(math.ceil(json_data['total'] / 100)) # calculate length of loop

## RUNS THE API PARSING ELEMENT IN EARNEST FOR THE TOTAL REQUIRED ITERATIONS ##
for i in range(0, iter_count):
	url = "https://explorer.roninchain.com/api/tokentxs?size=" + str(MAX_RESULTS) + "&addr=" + ronin_address + "&from=" + str(i*100)
	h = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36'}
	response = requests.get(url, headers=h)
	json_data = json.loads(response.text)

	result_set = pd.json_normalize(json_data, record_path = ['results'])
	df = df.append(result_set, ignore_index=True)
	print(str(i + 1) + ' out of ' + str(iter_count) + ' result sets retrieved.')

## DATE PROCESSING ##
df['timestamp_date'] = df['timestamp'].map(fix_timestamp)
df['date_time'] = df.apply(lambda x: datetime.datetime.fromtimestamp(x.timestamp), axis=1)
df['year'] = df['date_time'].dt.year
df = df[df['year'] <= 2021] # LIMITED TO JUST THE TAX YEAR + PRECEDING YEARS

## USD VALUE PROCESSING ##
df = df.merge(price_df, on=['token_symbol', 'timestamp_date'], how='left')

## SKY MAVIS SMART CONTRACT MAPPING ##
df['from_name'] = df['from'].map(axie_smart_contracts)
df['to_name'] = df['to'].map(axie_smart_contracts)

# TOKEN CALCULATIONS #
df['action'] = np.where(df['to'] == ronin_address, 'receipt', 'disposal')
df['modified_token_quantity'] =  df.apply(lambda x: fix_quantities(x.token_symbol, x.value), axis=1)
df['tx_value'] = pd.to_numeric(df['modified_token_quantity']) * df['price']

## EXPORT ALL TRANSACTIONS ##
df.to_csv(filepath + 'all transactions.csv', index=False)

## FILTER OUT ALL 0 VALUE TRANSACTIONS ##
df = df[df['modified_token_quantity'] !=0]

## FILTER OUT ALL LP TRANSACTIONS ##
lp_filter_string = r".*LP Contract"
lp_transactions = df[(df['to_name'].str.contains(lp_filter_string, regex=True, na=False)) | (df['from_name'].str.contains(lp_filter_string, regex=True, na=False))]
lp_transactions.to_csv(filepath + 'all LP transactions.csv', index=False)

df = df.drop(df[(df['to_name'].str.contains(lp_filter_string, regex=True, na=False)) | (df['from_name'].str.contains(lp_filter_string, regex=True, na=False))].index)

## SLP CALCULATIONS ##
slp_df = df[df['token_symbol'] == 'SLP']
slp_df.sort_values(by='timestamp', ascending=True, inplace=True)

slp_receipt_df = slp_df[slp_df['action'] == 'receipt']
slp_disposal_df = slp_df[slp_df['action'] == 'disposal']

x = TokenTracker()
for index, row in slp_receipt_df.iterrows():
    x.receipt(int(row['value']), (row['price']))

for index, row in slp_disposal_df.iterrows():
    slp_disposal_df.loc[index,'capital_gains'] = x.sell(int(row['value']), row['price'])

slp_disposal_df.to_csv(filepath + 'slp_disposals_with_capital_gains_calculated.csv', index=False)
slp_receipt_df.to_csv(filepath + 'slp_receipts_with_income_calculated.csv', index=False)

## AXS CALCULATIONS ##
axs_df = df[df['token_symbol'] == 'AXS']

axs_df = axs_df.drop(axs_df[(axs_df['to_name'] == 'AXS Staking Pool Contract') | (axs_df['from_name'] == 'AXS Staking Pool Contract') | (axs_df['from_name'] == 'Ronin Gateway Contract')].index)

axs_df.sort_values(by='timestamp', ascending=True, inplace=True)

axs_receipt_df = axs_df[axs_df['action'] == 'receipt']
axs_disposal_df = axs_df[axs_df['action'] == 'disposal']

x = TokenTracker()
for index, row in axs_receipt_df.iterrows():
    x.receipt(int(row['value']), (row['price']))

for index, row in axs_disposal_df.iterrows():
    axs_disposal_df.loc[index,'capital_gains'] = x.sell(row['modified_token_quantity'], row['price'])

axs_disposal_df.to_csv(filepath + 'axs_disposals_with_capital_gains_calculated.csv', index=False)
axs_receipt_df.to_csv(filepath + 'axs_receipts_no_capital_gains.csv', index=False)

## AXIE CALCULATIONS ##

### BREEDING FEE CALCULATIONS ###
df_breeding_txs = df[(df['from']=='0x0000000000000000000000000000000000000000') & (df['token_symbol']=='AXIE')]
df_breeding_txs = df_breeding_txs[['tx_hash', 'value', 'timestamp', 'timestamp_date']]

df_breeding_costs = df[['tx_hash', 'tx_value']]
df_breeding_costs = df_breeding_costs.groupby(['tx_hash'])['tx_value'].sum().reset_index()
df_breeding_costs = df_breeding_txs.merge(df_breeding_costs, on=['tx_hash'], how='inner')

### PURCHASE PRICE CALCULATIONS ###
df_axie_receipts = df[(df['to'] == ronin_address) & (df['token_symbol']=='AXIE')]
df_axie_receipts = df_axie_receipts[['tx_hash', 'value', 'timestamp', 'timestamp_date']]

df_weth_sends = df[(df['from'] == ronin_address) & (df['token_symbol']=='WETH')]
df_weth_sends = df_weth_sends[['tx_hash', 'modified_token_quantity', 'tx_value']]

df_axie_purchase_prices = df_weth_sends.merge(df_axie_receipts, on='tx_hash', how='inner')
df_axie_purchase_prices = df_axie_purchase_prices.groupby(['tx_hash', 'value', 'timestamp', 'timestamp_date'])['modified_token_quantity', 'tx_value'].sum().reset_index()

### SALES PRICE CALCULATIONS ###
df_axie_sends = df[(df['from'] == ronin_address) & (df['token_symbol']=='AXIE')]
df_axie_sends = df_axie_sends[['tx_hash', 'value', 'timestamp', 'timestamp_date']]

df_weth_receipts = df[(df['to'] == ronin_address) & (df['token_symbol']=='WETH')]
df_weth_receipts = df_weth_receipts[['tx_hash', 'modified_token_quantity', 'tx_value']]

df_axie_sale_prices = df_axie_sends.merge(df_weth_receipts, on='tx_hash', how='inner')

### REORGANIZE DFS AND STACK ###
df_axie_purchase_prices = df_axie_purchase_prices[['tx_hash', 'value', 'tx_value', 'timestamp', 'timestamp_date']]
df_axie_purchase_prices['source'] = 'Purchases'
df_axie_purchase_prices = df_axie_purchase_prices[['source', 'tx_hash', 'value', 'tx_value', 'timestamp', 'timestamp_date']]

df_breeding_costs['source'] = 'Breeding'
df_breeding_costs = df_breeding_costs[['source', 'tx_hash', 'value', 'tx_value', 'timestamp', 'timestamp_date']]

df_all_axie_intake = pd.concat([df_axie_purchase_prices, df_breeding_costs])
df_all_intake_with_sales = df_all_axie_intake.merge(df_axie_sale_prices, on='value', how='inner')
df_all_intake_with_sales = df_all_intake_with_sales[['source', 'value', 'tx_hash_x', 'tx_value_x', 'timestamp_x', 'timestamp_date_x', 'tx_hash_y', 'tx_value_y', 'timestamp_y', 'timestamp_date_y' ]]
df_all_intake_with_sales = df_all_intake_with_sales.rename(columns={'value': 'axie_id', 'tx_hash_x' : 'axie_basis_hash', 'tx_value_x' : 'axie_cost_basis', 'timestamp_x' : 'basis_timestamp', 'timestamp_date_x' : 'basis_timestamp_date', 'tx_hash_y' : 'axie_sales_hash', 'tx_value_y' : 'axie_sales_price', 'timestamp_y' : 'sales_timestamp', 'timestamp_date_y' : 'sales_timestamp_date'})
df_all_intake_with_sales['axie_sales_price'] = df_all_intake_with_sales['axie_sales_price'].replace({'' : 0})
df_all_intake_with_sales['tax_implications'] = df_all_intake_with_sales['axie_sales_price'] - df_all_intake_with_sales['axie_cost_basis']
df_all_intake_with_sales.to_csv(filepath + 'axie sales.csv', index=False)

# MISCELLANEOUS #

## DEPOSITS ##
df_all_deposits_to_axie = df[df['from_name']=='Ronin Gateway Contract']
df_all_deposits_to_axie.to_csv(filepath + 'all_deposits_to_axie.csv', index=False)

## WITHDRAWALS ##
df_all_withdrawals_from_axie = df[df['to_name']=='Ronin Gateway Contract']
df_all_withdrawals_from_axie.to_csv(filepath + 'all_withdrawals_from_axie.csv', index=False)
