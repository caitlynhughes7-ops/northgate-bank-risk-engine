/*--------------------------------------------------------------------------
  m_ext_product_reference.sas
  Source extract - Product code reference data
  Source system: Reference data   Frequency: monthly
  Landing: &INBOUND./product_reference_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_product_reference(period=, outds=stg.product_reference);
  %log_step(ext_product_reference, msg=&period);

  filename src_product_reference "&INBOUND./product_reference_&period..csv";

  proc import datafile=src_product_reference out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* the header row is repeated part way through the file in some months */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if missing(EXTRACT_PERIOD) then delete;
  run;

  %assert_rows(&outds, minrows=10);

  /* Reference data occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [product_reference] extract contains multiple periods;
%mend;
