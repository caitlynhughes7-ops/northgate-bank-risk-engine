/*--------------------------------------------------------------------------
  m_ext_securitisation.sas
  Source extract - Securitised pool membership
  Source system: Trust reporting   Frequency: monthly
  Landing: &INBOUND./securitisation_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_securitisation(period=, outds=stg.securitisation);
  %log_step(ext_securitisation, msg=&period);

  filename src_securitisation "&INBOUND./securitisation_&period..csv";

  proc import datafile=src_securitisation out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* account ids arrive zero padded from this source and unpadded from others */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if missing(EXTRACT_PERIOD) then delete;
  run;

  %assert_rows(&outds, minrows=10);

  /* Trust reporting occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [securitisation] extract contains multiple periods;
%mend;
