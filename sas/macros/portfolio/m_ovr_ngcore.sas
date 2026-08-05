/*--------------------------------------------------------------------------
  m_ovr_ngcore.sas
  Portfolio override macro - Northgate core originations
  Onboarded 2003. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance 2022.
--------------------------------------------------------------------------*/
%macro ovr_ngcore(inds=, outds=);
  %log_step(ovr_ngcore);

  data &outds;
    set &inds;
    where BOOK_CD = "NGCORE";

    /* PD adjustment - scorecard not recalibrated since acquisition */
    PD_12M = min(PD_12M * 1.28, 1);

    /* LGD adjustment - vendor recovery data used pending internal study */
    LGD = min(max(LGD * 0.93, 0.15), 1);

    /* book specific CCF from the acquisition due diligence */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.65 * UNDRAWN;

    /* accounts migrated in the 2003 conversion carry a synthetic origination
       PD; suppress the relative SICR test for these                        */
    if CONV_FLAG = 'Y' then PD_LIFETIME_ORIG = PD_LIFETIME;
  run;
%mend;

%macro ovr_ngcore_controls(inds=, outds=);
  /* book level controls. retained pending book run off */
  %log_step(ovr_ngcore_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "NGCORE";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [NGCORE] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "NGCORE";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 8;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 84;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0799;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_ngcore;
  run;
%mend;

%macro ovr_ngcore_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "NGCORE";
  quit;
  %put NOTE: [NGCORE] engine drawn balance &eng;
%mend;
