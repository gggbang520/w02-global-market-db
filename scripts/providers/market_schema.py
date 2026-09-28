SCHEMA_VERSION='stock_daily_v1'
REQUIRED_FIELDS=['listing_id','security_id','ticker','exchange_mic','trade_date','open','high','low','close','volume','turnover','currency','source_id']

def validate_schema(record):
 return all(k in record for k in REQUIRED_FIELDS)
