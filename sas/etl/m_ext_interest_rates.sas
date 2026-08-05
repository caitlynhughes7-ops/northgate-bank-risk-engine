/*--------------------------------------------------------------------------
  m_ext_interest_rates.sas
  Source extract - Instrument effective interest rates
  Source system: Mortgage servicing   Frequency: monthly
  Landing: &INBOUND./interest_rates_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_interest_rates(period=, outds=stg.interest_rates);
  %log_step(ext_interest_rates, msg=&period);

  filename src_interest_rates "&INBOUND./interest_rates_&period..csv";

  proc import datafile=src_interest_rates out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* amounts are signed the other way round on this feed */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if missing(EXTRACT_PERIOD) then delete;
  run;

  %assert_rows(&outds, minrows=1000);

  /* Mortgage servicing occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [interest_rates] extract contains multiple periods;
%mend;
