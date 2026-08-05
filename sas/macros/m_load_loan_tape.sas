%macro load_loan_tape(period=, outds=stg.loan_tape);
  %log_step(load_loan_tape, msg=period &period);

  filename tape "&INBOUND./loan_tape_&period..csv";

  proc import datafile=tape out=&outds dbms=csv replace;
    getnames=yes;
    guessingrows=max;
  run;

  /* the source system pads account ids to 12 chars in some months and not others */
  data &outds;
    set &outds;
    ACCOUNT_ID = left(compress(ACCOUNT_ID));
    if missing(DRAWN_BAL) then DRAWN_BAL = 0;
    if missing(UNDRAWN)   then UNDRAWN   = 0;
  run;

  %assert_rows(&outds, minrows=100);

  filename tape2 "&INBOUND./collateral_&period..csv";
  proc import datafile=tape2 out=stg.collateral dbms=csv replace;
    getnames=yes;
  run;
%mend;
