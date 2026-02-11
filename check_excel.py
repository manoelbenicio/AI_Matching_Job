"""
Examine Excel file structure for job import
"""
import pandas as pd

df = pd.read_excel(r'D:\VMs\Projetos\RFP_Automation_VF\AI_Job_Matcher\Jobs_Linkedin_PROD_8_2_2026.xlsx')
print('='*60)
print(f'Total jobs in Excel: {len(df)}')
print('='*60)
print('\nAll columns:')
for i, col in enumerate(df.columns):
    sample_val = str(df[col].iloc[0])[:50] if pd.notna(df[col].iloc[0]) else 'NaN'
    print(f'  {i+1}. {col}: {sample_val}...')

# Look for date columns
date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower() or 'posted' in c.lower()]
print(f'\nDate-related columns: {date_cols}')
if date_cols:
    for col in date_cols:
        print(f'\n{col} samples:')
        print(df[col].value_counts().head(10))
