# axie-profit-loss-calculator
This is a script to easily calculate the tax implications of all Axie Infinity transactions.

There are (currently) two parts to this repo: a csv of token prices and the script itself.

The csv is used as a stand in for a token price API call.  In the script I originally used the CoinGecko API
for this purpose (and left the function in there), however I was not able to rely on it due to rate limiting for 
free users.  If you have an API key, this may be a better route for you.  This csv is also incomplete at the time of
this writing, but I intend to fill it in with missing 2021 dates as time permits.  If you use this before then, you may
have to do that yourself, sorry. Token prices are taken directly from the Coin Gecko website, and are as of 18:00 each day,
so the 'true' profit and loss on these calculations may be off a bit.  Sorry again!  
Lastly, the date format on the csv is DD-MM-YYYY.  If you complete this file on your own
make sure you do not mix up the days/months or you will have a bad time.

The script itself requires you to fill in your ronin address and a filepath where you will store the aforementioned csv.
This is also where the outputs from the script will go.  The script currently has no way of dealing with Ronin LP transactions,
so you're on your own there.  I left them in for posterity, but I'm not sure if they're being handled properly.  Sorry!

If you have any suggestions on improving this script or for adding missing features, please submit a PR.  I am new to Python and
software development in general, and would be grateful for the opportunity to learn more from the masters lurking Github.

Special thanks to Shraknard/pyaxie and mdichtler/ronin-api-wrapper for inspiration and for directly informing some of the functions,
the wonderful Maxbrand99 for assistance understanding some of the Ronin API behaviors,
and brawndojo on Youtube for helping me learn how to implement a price/quantity queue.

If you found this helpful, please consider an Ethereum donation here: 0xdedB0c92e730CdA6323fDFfc60f26D2495e09Eed
