/*--------------------------------------------------------------------------
  m_ovr_pennine.sas
  Portfolio override macro - Pennine Home Loans (acquired 2014)
  Onboarded 2014. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2019.
--------------------------------------------------------------------------*/
%macro ovr_pennine(inds=, outds=);
  %log_step(ovr_pennine);

  data &outds;
    set &inds;
    where BOOK_CD = "PENNINE";

    /* PD adjustment - scorecard not recalibrated since acquisition */
    PD_12M = min(PD_12M * 1.43, 1);

    /* LGD adjustment - vendor recovery data used pending internal study */
    LGD = min(max(LGD * 1.01, 0.10), 1);

    /* CCF differs from group standard, retained for comparability */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.75 * UNDRAWN;

    /* legacy system does not supply the watchlist flag for this book */
    WATCHLIST_FL = 0;
  run;
%mend;

%macro ovr_pennine_controls(inds=, outds=);
  /* book level controls. owner left the bank in 2022 */
  %log_step(ovr_pennine_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "PENNINE";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [PENNINE] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "PENNINE";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 10;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 60;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0499;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_pennine;
  run;
%mend;

%macro ovr_pennine_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "PENNINE";
  quit;
  %put NOTE: [PENNINE] engine drawn balance &eng;
%mend;
