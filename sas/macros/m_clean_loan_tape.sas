%macro clean_loan_tape(inds=stg.loan_tape, outds=stg.tape_clean);
  %log_step(clean_loan_tape);

  data &outds;
    set &inds;

    /* ---- arrears -------------------------------------------------------
       DPD arrives as a character field with occasional 'N/A' and '999'
       sentinel values from the legacy collections platform.            */
    if DPD in ('N/A','','.','NULL') then _dpd = 0;
    else if input(DPD, best12.) = 999 then _dpd = 0;  /* sentinel = closed */
    else _dpd = input(DPD, best12.);
    drop DPD;
    rename _dpd = DPD_N;

    /* ---- flags ---------------------------------------------------------*/
    FORBEARANCE_FL = (upcase(FORBEARANCE) in ('Y','YES','1'));
    WATCHLIST_FL   = (upcase(WATCHLIST)   in ('Y','YES','1'));
    DEFAULT_FL     = (upcase(DEFAULT_IND) in ('Y','YES','1'));
    drop FORBEARANCE WATCHLIST DEFAULT_IND;

    /* interest only accounts carry a zero repayment amount, not missing  */
    if IO_FLAG = 'Y' then MONTHLY_PAYMENT = 0;

    /* EIR is stored as a percentage on the mortgage feed and a decimal on
       the unsecured feed. Normalise to decimal.                          */
    if EIR > 1 then EIR = EIR / 100;
  run;

  %assert_rows(&outds, minrows=100);
%mend;
