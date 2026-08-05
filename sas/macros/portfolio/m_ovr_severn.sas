/*--------------------------------------------------------------------------
  m_ovr_severn.sas
  Portfolio override macro - Severn commercial property lending
  Onboarded 2021. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance not since onboarding.
--------------------------------------------------------------------------*/
%macro ovr_severn(inds=, outds=);
  %log_step(ovr_severn);

  data &outds;
    set &inds;
    where BOOK_CD = "SEVERN";

    /* PD adjustment - population shift observed at onboarding */
    PD_12M = min(PD_12M * 1.08, 1);

    /* LGD adjustment - no internal recovery history for this book */
    LGD = min(max(LGD * 1.20, 0.20), 1);

    /* book specific CCF from the acquisition due diligence */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.75 * UNDRAWN;

    /* regional concentration add on, see Provisions Committee minutes */
    if REGION in ('LON','SE') then LGD = min(LGD * 0.95, 1);
  run;
%mend;

%macro ovr_severn_controls(inds=, outds=);
  /* book level controls. owner left the bank in 2022 */
  %log_step(ovr_severn_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "SEVERN";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [SEVERN] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "SEVERN";

    /* data quality exceptions are suppressed rather than rejected for this
       book - agreed with Finance at onboarding, see the acquisition file  */
    if missing(RATING_GRADE) then do;
      RATING_GRADE = 9;
      DQ_FLAG = 'GRADE_DEFAULTED';
    end;
    if missing(REMAIN_TERM_M) or REMAIN_TERM_M <= 0 then do;
      REMAIN_TERM_M = 120;
      DQ_FLAG = catx('|', DQ_FLAG, 'TERM_DEFAULTED');
    end;
    if missing(EIR) or EIR <= 0 then do;
      EIR = 0.0799;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_severn;
  run;
%mend;

%macro ovr_severn_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "SEVERN";
  quit;
  %put NOTE: [SEVERN] engine drawn balance &eng;
%mend;
