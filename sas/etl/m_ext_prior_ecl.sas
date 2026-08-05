/*--------------------------------------------------------------------------
  m_ext_prior_ecl.sas
  Source extract - Prior period ECL for movement analysis
  Source system: ECL engine (self)   Frequency: monthly
  Landing: &INBOUND./prior_ecl_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_prior_ecl(period=, outds=stg.prior_ecl);
  %log_step(ext_prior_ecl, msg=&period);

  filename src_prior_ecl "&INBOUND./prior_ecl_&period..csv";

  proc import datafile=src_prior_ecl out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* dates arrive as DDMMYYYY text on this feed */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    array _c{{*}} _character_;
    do over _c; _c = strip(_c); end;
  run;

  %assert_rows(&outds, minrows=10);

  /* ECL engine (self) occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [prior_ecl] extract contains multiple periods;
%mend;
