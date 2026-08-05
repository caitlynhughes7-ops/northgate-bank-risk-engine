/*--------------------------------------------------------------------------
  m_ext_limit_management.sas
  Source extract - Card and overdraft limits
  Source system: Vision Plus   Frequency: daily
  Landing: &INBOUND./limit_management_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_limit_management(period=, outds=stg.limit_management);
  %log_step(ext_limit_management, msg=&period);

  filename src_limit_management "&INBOUND./limit_management_&period..csv";

  proc import datafile=src_limit_management out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* amounts are signed the other way round on this feed */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if upcase(RECORD_TYPE) = 'HEADER' then delete;
  run;

  %assert_rows(&outds, minrows=500);

  /* Vision Plus occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [limit_management] extract contains multiple periods;
%mend;
