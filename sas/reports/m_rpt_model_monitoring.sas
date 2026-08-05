/*--------------------------------------------------------------------------
  m_rpt_model_monitoring.sas
  Model monitoring - population stability
  Output: &OUTBOUND./model_monitoring_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_model_monitoring(inds=stg.ecl_acct, period=);
  %log_step(rpt_model_monitoring);

  proc sql;
    create table stg.rpt_model_monitoring as
    select SEGMENT, STAGE,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           mean(PD_LIFETIME) as AVG_PD_LIFETIME format=percent9.4
    from &inds
    where DEFAULT_FL = 1
    group by SEGMENT, STAGE
    order by SEGMENT, STAGE;
  quit;

  proc export data=stg.rpt_model_monitoring
       outfile="&OUTBOUND./model_monitoring_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_model_monitoring_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the the CFO's office control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_model_monitoring where EAD is null;
    select count(*) into :n_neg  from stg.rpt_model_monitoring where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_model_monitoring;
  quit;

  %if &n_null > 0 %then %put ERROR: [model_monitoring] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [model_monitoring] &n_neg rows with negative ECL;
  %put NOTE: [model_monitoring] submission total ECL &tot;

  /* prior period comparison - variance over 15% is queried by the CFO's office */
  proc sql;
    create table stg.rpt_model_monitoring_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_model_monitoring as c
    left join hist.rpt_model_monitoring_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT and c.STAGE = p.STAGE;
  quit;

  data _null_;
    set stg.rpt_model_monitoring_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.15 then
      put "WARNING: [model_monitoring] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_model_monitoring_archive(period=);
  /* retained for 10 years per the group records retention schedule */
  data hist.rpt_model_monitoring_&period.;
    set stg.rpt_model_monitoring;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_model_monitoring_var;
  quit;
%mend;
