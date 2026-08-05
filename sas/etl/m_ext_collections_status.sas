/*--------------------------------------------------------------------------
  m_ext_collections_status.sas
  Source extract - Collections and recoveries status
  Source system: Tallyman   Frequency: daily
  Landing: &INBOUND./collections_status_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_collections_status(period=, outds=stg.collections_status);
  %log_step(ext_collections_status, msg=&period);

  filename src_collections_status "&INBOUND./collections_status_&period..csv";

  proc import datafile=src_collections_status out=&outds dbms=csv replace;
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

  /* Tallyman occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [collections_status] extract contains multiple periods;
%mend;
