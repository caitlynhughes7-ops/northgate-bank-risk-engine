/*--------------------------------------------------------------------------
  m_ovr_trent.sas
  Portfolio override macro - Trent SME lending
  Onboarded 2017. Applies book specific adjustments agreed at acquisition
  and retained for comparability. Reviewed by Model Governance not since onboarding.
--------------------------------------------------------------------------*/
%macro ovr_trent(inds=, outds=);
  %log_step(ovr_trent);

  data &outds;
    set &inds;
    where BOOK_CD = "TRENT";

    /* PD adjustment - grade migration adjustment */
    PD_12M = min(PD_12M * 1.35, 1);

    /* LGD adjustment - no internal recovery history for this book */
    LGD = min(max(LGD * 1.05, 0.10), 1);

    /* CCF differs from group standard, retained for comparability */
    if UNDRAWN > 0 then EAD = DRAWN_BAL + 0.65 * UNDRAWN;

    /* forced sale discount already embedded in the valuation for this book,
       so the standard haircut is not applied again                        */
    HAIRCUT_OVERRIDE = 0;
  run;
%mend;

%macro ovr_trent_controls(inds=, outds=);
  /* book level controls. owner left the bank in 2022 */
  %log_step(ovr_trent_controls);

  proc sql noprint;
    select count(*) into :n_book from &inds where BOOK_CD = "TRENT";
  quit;
  %if &n_book = 0 %then %do;
    %put WARNING: [TRENT] no exposures found for this book;
  %end;

  data &outds;
    set &inds;
    where BOOK_CD = "TRENT";

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
      EIR = 0.0625;
      DQ_FLAG = catx('|', DQ_FLAG, 'EIR_DEFAULTED');
    end;
  run;

  proc freq data=&outds noprint;
    tables DQ_FLAG / out=stg.dq_trent;
  run;
%mend;

%macro ovr_trent_recon(inds=);
  /* reconciles the book back to the source ledger extract */
  %local src eng;
  proc sql noprint;
    select sum(DRAWN_BAL) into :eng from &inds where BOOK_CD = "TRENT";
  quit;
  %put NOTE: [TRENT] engine drawn balance &eng;
%mend;
