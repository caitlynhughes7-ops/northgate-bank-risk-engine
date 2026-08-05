/*--------------------------------------------------------------------------
  m_rpt_prior_period_compare.sas
  Prior period comparison and variance analysis
  Output: &OUTBOUND./prior_period_compare_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_prior_period_compare(inds=stg.ecl_acct, period=);
  %log_step(rpt_prior_period_compare);

  proc sql;
    create table stg.rpt_prior_period_compare as
    select SEGMENT,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           sum(ECL)/sum(EAD) as COVERAGE format=percent9.4
    from &inds
    where FORBEARANCE_FL = 1
    group by SEGMENT
    order by SEGMENT;
  quit;

  proc export data=stg.rpt_prior_period_compare
       outfile="&OUTBOUND./prior_period_compare_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_prior_period_compare_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Internal Audit control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_prior_period_compare where EAD is null;
    select count(*) into :n_neg  from stg.rpt_prior_period_compare where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_prior_period_compare;
  quit;

  %if &n_null > 0 %then %put ERROR: [prior_period_compare] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [prior_period_compare] &n_neg rows with negative ECL;
  %put NOTE: [prior_period_compare] submission total ECL &tot;

  /* prior period comparison - variance over 15% is queried by Internal Audit */
  proc sql;
    create table stg.rpt_prior_period_compare_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_prior_period_compare as c
    left join hist.rpt_prior_period_compare_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_prior_period_compare_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.15 then
      put "WARNING: [prior_period_compare] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_prior_period_compare_archive(period=);
  /* retained for 7 years per the group records retention schedule */
  data hist.rpt_prior_period_compare_&period.;
    set stg.rpt_prior_period_compare;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_prior_period_compare_var;
  quit;
%mend;
