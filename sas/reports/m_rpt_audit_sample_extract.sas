/*--------------------------------------------------------------------------
  m_rpt_audit_sample_extract.sas
  Internal Audit sampling extract
  Output: &OUTBOUND./audit_sample_extract_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_audit_sample_extract(inds=stg.ecl_acct, period=);
  %log_step(rpt_audit_sample_extract);

  proc sql;
    create table stg.rpt_audit_sample_extract as
    select SEGMENT, SICR_REASON,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           sum(ECL)/sum(EAD) as COVERAGE format=percent9.4
    from &inds
    group by SEGMENT, SICR_REASON
    order by SEGMENT, SICR_REASON;
  quit;

  proc export data=stg.rpt_audit_sample_extract
       outfile="&OUTBOUND./audit_sample_extract_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_audit_sample_extract_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the the CFO's office control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_audit_sample_extract where EAD is null;
    select count(*) into :n_neg  from stg.rpt_audit_sample_extract where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_audit_sample_extract;
  quit;

  %if &n_null > 0 %then %put ERROR: [audit_sample_extract] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [audit_sample_extract] &n_neg rows with negative ECL;
  %put NOTE: [audit_sample_extract] submission total ECL &tot;

  /* prior period comparison - variance over 15% is queried by the CFO's office */
  proc sql;
    create table stg.rpt_audit_sample_extract_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_audit_sample_extract as c
    left join hist.rpt_audit_sample_extract_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_audit_sample_extract_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.15 then
      put "WARNING: [audit_sample_extract] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_audit_sample_extract_archive(period=);
  /* retained for 10 years per the group records retention schedule */
  data hist.rpt_audit_sample_extract_&period.;
    set stg.rpt_audit_sample_extract;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_audit_sample_extract_var;
  quit;
%mend;
