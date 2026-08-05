/*--------------------------------------------------------------------------
  m_ovr_ashdown.sas
  Portfolio override macro - Ashdown second charge book
  Onboarded 2019. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance not since onboarding.
--------------------------------------------------------------------------*/
%macro ovr_ashdown(inds=, outds=);
  %log_step(ovr_ashdown);

  data &outds;
    set &inds;
    where BOOK_CD = "ASHDOWN";

    /* PD adjustment - vendor scorecard mapped to internal masterscale */
    PD_12M = min(PD_12M * 1.18, 1);

    /* LGD adjustment - recovery experience below group average */
    LGD = min(max(LGD * 0.95, 0.20), 1);

    /* CCF differs from group standard, retained for comparability */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.45 * UNDRAWN;

    /* interest only maturity risk uplift agreed with Credit Risk 2019 */
    if IO_FLAG = 'Y' and REMAIN_TERM_M <= 24 then PD_12M = min(PD_12M * 1.40, 1);
  run;
%mend;

%macro ovr_ashdown_controls(inds=, outds=);
  /* book level controls. retained pending book run off */
  %log_step(ovr_ashdown_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "ASHDOWN";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [ASHDOWN] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "ASHDOWN";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 8;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 60;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0625;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_ashdown;
  run;
%mend;

%macro ovr_ashdown_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "ASHDOWN";
  quit;
  %put NOTE: [ASHDOWN] engine drawn balance &eng;
%mend;
