/*--------------------------------------------------------------------------
  m_ext_default_register.sas
  Source extract - Group default register
  Source system: Credit Risk   Frequency: monthly
  Landing: &INBOUND./default_register_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_default_register(period=, outds=stg.default_register);
  %log_step(ext_default_register, msg=&period);

  filename src_default_register "&INBOUND./default_register_&period..csv";

  proc import datafile=src_default_register out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* the source pads with trailing spaces which breaks the downstream merge */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if upcase(RECORD_TYPE) = 'HEADER' then delete;
  run;

  %assert_rows(&outds, minrows=50);

  /* Credit Risk occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [default_register] extract contains multiple periods;
%mend;
