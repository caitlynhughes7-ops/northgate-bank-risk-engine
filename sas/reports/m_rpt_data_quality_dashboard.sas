/*--------------------------------------------------------------------------
  m_rpt_data_quality_dashboard.sas
  Data quality exception dashboard extract
  Output: &OUTBOUND./data_quality_dashboard_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_data_quality_dashboard(inds=stg.ecl_acct, period=);
  %log_step(rpt_data_quality_dashboard);

  proc sql;
    create table stg.rpt_data_quality_dashboard as
    select STAGE,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    where STAGE in (2,3)
    group by STAGE
    order by STAGE;
  quit;

  proc export data=stg.rpt_data_quality_dashboard
       outfile="&OUTBOUND./data_quality_dashboard_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_data_quality_dashboard_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the the CFO's office control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_data_quality_dashboard where EAD is null;
    select count(*) into :n_neg  from stg.rpt_data_quality_dashboard where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_data_quality_dashboard;
  quit;

  %if &n_null > 0 %then %put ERROR: [data_quality_dashboard] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [data_quality_dashboard] &n_neg rows with negative ECL;
  %put NOTE: [data_quality_dashboard] submission total ECL &tot;

  /* prior period comparison - variance over 5% is queried by the CFO's office */
  proc sql;
    create table stg.rpt_data_quality_dashboard_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_data_quality_dashboard as c
    left join hist.rpt_data_quality_dashboard_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_data_quality_dashboard_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.05 then
      put "WARNING: [data_quality_dashboard] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_data_quality_dashboard_archive(period=);
  /* retained for 6 years per the group records retention schedule */
  data hist.rpt_data_quality_dashboard_&period.;
    set stg.rpt_data_quality_dashboard;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_data_quality_dashboard_var;
  quit;
%mend;
