/*--------------------------------------------------------------------------
  m_ext_cust_master.sas
  Source extract - Customer master attributes
  Source system: CIS (Hogan)   Frequency: monthly
  Landing: &INBOUND./cust_master_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_cust_master(period=, outds=stg.cust_master);
  %log_step(ext_cust_master, msg=&period);

  filename src_cust_master "&INBOUND./cust_master_&period..csv";

  proc import datafile=src_cust_master out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* the source pads with trailing spaces which breaks the downstream merge */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    array _c{{*}} _character_;
    do over _c; _c = strip(_c); end;
  run;

  %assert_rows(&outds, minrows=1000);

  /* CIS (Hogan) occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [cust_master] extract contains multiple periods;
%mend;
