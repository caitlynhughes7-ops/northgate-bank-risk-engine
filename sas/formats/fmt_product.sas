proc format;
  value $seg
    'RETAIL_MORTGAGE' = 'Retail mortgages'
    'BTL_MORTGAGE'    = 'Buy to let'
    'PERSONAL_LOAN'   = 'Personal loans'
    'CREDIT_CARD'     = 'Credit cards'
    'OVERDRAFT'       = 'Overdrafts'
    'SME_TERM'        = 'SME lending'
    other             = 'Unclassified';

  value stage
    1 = 'Stage 1 - 12m ECL'
    2 = 'Stage 2 - lifetime ECL'
    3 = 'Stage 3 - credit impaired';
run;
