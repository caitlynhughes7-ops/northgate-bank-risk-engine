/*--------------------------------------------------------------------------
  m_ext_gl_balances.sas
  Source extract - General ledger balances
  Source system: SAP   Frequency: monthly
  Landing: &INBOUND./gl_balances_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_gl_balances(period=, outds=stg.gl_balances);
  %log_step(ext_gl_balances, msg=&period);

  filename src_gl_balances "&INBOUND./gl_balances_&period..csv";

  proc import datafile=src_gl_balances out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* amounts are signed the other way round on this feed */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    array _c{{*}} _character_;
    do over _c; _c = strip(_c); end;
  run;

  %assert_rows(&outds, minrows=100);

  /* SAP occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [gl_balances] extract contains multiple periods;
%mend;
