/*--------------------------------------------------------------------------
  m_ovr_lowry.sas
  Portfolio override macro - Lowry SME asset finance
  Onboarded 2020. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2019.
--------------------------------------------------------------------------*/
%macro ovr_lowry(inds=, outds=);
  %log_step(ovr_lowry);

  data &outds;
    set &inds;
    where BOOK_CD = "LOWRY";

    /* PD adjustment - vendor scorecard mapped to internal masterscale */
    PD_12M = min(PD_12M * 1.24, 1);

    /* LGD adjustment - recovery experience below group average */
    LGD = min(max(LGD * 1.18, 0.15), 1);

    /* legacy limit management platform, CCF calibrated 2019 */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.45 * UNDRAWN;

    /* interest only maturity risk uplift agreed with Credit Risk 2020 */
    if IO_FLAG = 'Y' and REMAIN_TERM_M <= 24 then PD_12M = min(PD_12M * 1.40, 1);
  run;
%mend;

%macro ovr_lowry_controls(inds=, outds=);
  /* book level controls. owner left the bank in 2022 */
  %log_step(ovr_lowry_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "LOWRY";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [LOWRY] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "LOWRY";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 9;
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
    tables DQ_FLAG / out=stg.dq_lowry;
  run;
%mend;

%macro ovr_lowry_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "LOWRY";
  quit;
  %put NOTE: [LOWRY] engine drawn balance &eng;
%mend;
