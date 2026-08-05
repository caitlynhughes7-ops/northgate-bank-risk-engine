/*--------------------------------------------------------------------------
  m_rpt_irb_backtest_pd.sas
  IRB PD backtesting extract
  Output: &OUTBOUND./irb_backtest_pd_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_irb_backtest_pd(inds=stg.ecl_acct, period=);
  %log_step(rpt_irb_backtest_pd);

  proc sql;
    create table stg.rpt_irb_backtest_pd as
    select SEGMENT, STAGE,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    where STAGE in (2,3)
    group by SEGMENT, STAGE
    order by SEGMENT, STAGE;
  quit;

  proc export data=stg.rpt_irb_backtest_pd
       outfile="&OUTBOUND./irb_backtest_pd_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_irb_backtest_pd_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the the CFO's office control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_irb_backtest_pd where EAD is null;
    select count(*) into :n_neg  from stg.rpt_irb_backtest_pd where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_irb_backtest_pd;
  quit;

  %if &n_null > 0 %then %put ERROR: [irb_backtest_pd] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [irb_backtest_pd] &n_neg rows with negative ECL;
  %put NOTE: [irb_backtest_pd] submission total ECL &tot;

  /* prior period comparison - variance over 5% is queried by the CFO's office */
  proc sql;
    create table stg.rpt_irb_backtest_pd_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_irb_backtest_pd as c
    left join hist.rpt_irb_backtest_pd_&PRIOR_YYYYMM as p
      on c.BOOK_CD = p.BOOK_CD;
  quit;

  data _null_;
    set stg.rpt_irb_backtest_pd_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.10 then
      put "WARNING: [irb_backtest_pd] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_irb_backtest_pd_archive(period=);
  /* retained for 6 years per the group records retention schedule */
  data hist.rpt_irb_backtest_pd_&period.;
    set stg.rpt_irb_backtest_pd;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_irb_backtest_pd_var;
  quit;
%mend;
