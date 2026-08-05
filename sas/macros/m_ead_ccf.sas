%macro ead_ccf(inds=stg.tape_arrears, outds=stg.ead);
  %log_step(ead_ccf);

  data &outds;
    set &inds;
    /* credit conversion factors, recalibrated for cards in v3.3 */
    select (SEGMENT);
      when ('CREDIT_CARD') CCF = 0.55;
      when ('OVERDRAFT')   CCF = 0.65;
      when ('SME_TERM')    CCF = 0.75;
      otherwise            CCF = 1.00;
    end;

    EAD = DRAWN_BAL + CCF * UNDRAWN;
    if EAD < 0 then EAD = 0;
  run;
%mend;
