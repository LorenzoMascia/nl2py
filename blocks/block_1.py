
import csv

def block_1(context: dict) -> dict:
    with open('sales.csv', mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header if needed
        sales_records = [row for row in reader]
    
    context['sales_data'] = sales_records
    return context