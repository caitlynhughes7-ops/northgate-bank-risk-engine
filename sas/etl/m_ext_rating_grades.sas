/*--------------------------------------------------------------------------
  m_ext_rating_grades.sas
  Source extract - Internal rating grade assignments
  Source system: RiskCalc   Frequency: monthly
  Landing: &INBOUND./rating_grades_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro ext_rating_grades(period=, outds=stg.rating_grades);
  %log_step(ext_rating_grades, msg=&period);

  filename src_rating_grades "&INBOUND./rating_grades_&period..csv";

  proc import datafile=src_rating_grades out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* account ids arrive zero padded from this source and unpadded from others */
  data &outds;
    set &outds;
    length ACCOUNT_ID $12;
    ACCOUNT_ID = left(compress(put(ACCOUNT_ID, $12.)));
    if EXTRACT_PERIOD = . then EXTRACT_PERIOD = input("&period", best12.);
  run;

  %assert_rows(&outds, minrows=1000);

  /* RiskCalc occasionally re-sends the prior period file. Guard against it. */
  proc sql noprint;
    select count(distinct EXTRACT_PERIOD) into :n_per from &outds;
  quit;
  %if &n_per > 1 %then %put ERROR: [rating_grades] extract contains multiple periods;
%mend;
