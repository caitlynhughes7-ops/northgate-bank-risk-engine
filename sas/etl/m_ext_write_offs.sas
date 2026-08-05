/*--------------------------------------------------------------------------
  m_ext_write_offs.sas
  Source extract - Write off and recovery postings
  Source system: SAP   Frequency: monthly
  Landing: &INBOUND./write_offs_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_write_offs(period=, outds=stg.write_offs);
  %log_step(ext_write_offs, msg=&period);

  filename src_write_offs "&INBOUND./write_offs_&period..csv";

  proc import datafile=src_write_offs out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* the source pads with trailing spaces which breaks the downstream merge */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if EXTRACT_PERIOD = . then EXTRACT_PERIOD = input("&period", best12.);
  run;

  %assert_rows(&outds, minrows=10);

  /* SAP occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [write_offs] extract contains multiple periods;
%mend;
