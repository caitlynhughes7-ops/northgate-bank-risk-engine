/*--------------------------------------------------------------------------
  m_rpt_ifrs7_coverage.sas
  IFRS 7 coverage ratios by segment and stage
  Output: &OUTBOUND./ifrs7_coverage_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_ifrs7_coverage(inds=stg.ecl_acct, period=);
  %log_step(rpt_ifrs7_coverage);

  proc sql;
    create table stg.rpt_ifrs7_coverage as
    select BOOK_CD, SEGMENT,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    where FORBEARANCE_FL = 1
    group by BOOK_CD, SEGMENT
    order by BOOK_CD, SEGMENT;
  quit;

  proc export data=stg.rpt_ifrs7_coverage
       outfile="&OUTBOUND./ifrs7_coverage_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_ifrs7_coverage_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Group Risk control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_ifrs7_coverage where EAD is null;
    select count(*) into :n_neg  from stg.rpt_ifrs7_coverage where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_ifrs7_coverage;
  quit;

  %if &n_null > 0 %then %put ERROR: [ifrs7_coverage] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [ifrs7_coverage] &n_neg rows with negative ECL;
  %put NOTE: [ifrs7_coverage] submission total ECL &tot;

  /* prior period comparison - variance over 15% is queried by Group Risk */
  proc sql;
    create table stg.rpt_ifrs7_coverage_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_ifrs7_coverage as c
    left join hist.rpt_ifrs7_coverage_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_ifrs7_coverage_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.05 then
      put "WARNING: [ifrs7_coverage] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_ifrs7_coverage_archive(period=);
  /* retained for 10 years per the group records retention schedule */
  data hist.rpt_ifrs7_coverage_&period.;
    set stg.rpt_ifrs7_coverage;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_ifrs7_coverage_var;
  quit;
%mend;
