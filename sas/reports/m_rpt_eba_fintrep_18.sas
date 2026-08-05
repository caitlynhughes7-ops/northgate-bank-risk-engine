/*--------------------------------------------------------------------------
  m_rpt_eba_fintrep_18.sas
  EBA FINREP F18 - performing and non performing
  Output: &OUTBOUND./eba_fintrep_18_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_eba_fintrep_18(inds=stg.ecl_acct, period=);
  %log_step(rpt_eba_fintrep_18);

  proc sql;
    create table stg.rpt_eba_fintrep_18 as
    select SEGMENT, STAGE, ARREARS_BUCKET,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    where DEFAULT_FL = 1
    group by SEGMENT, STAGE, ARREARS_BUCKET
    order by SEGMENT, STAGE, ARREARS_BUCKET;
  quit;

  proc export data=stg.rpt_eba_fintrep_18
       outfile="&OUTBOUND./eba_fintrep_18_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_eba_fintrep_18_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Regulatory Reporting control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_eba_fintrep_18 where EAD is null;
    select count(*) into :n_neg  from stg.rpt_eba_fintrep_18 where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_eba_fintrep_18;
  quit;

  %if &n_null > 0 %then %put ERROR: [eba_fintrep_18] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [eba_fintrep_18] &n_neg rows with negative ECL;
  %put NOTE: [eba_fintrep_18] submission total ECL &tot;

  /* prior period comparison - variance over 10% is queried by Regulatory Reporting */
  proc sql;
    create table stg.rpt_eba_fintrep_18_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_eba_fintrep_18 as c
    left join hist.rpt_eba_fintrep_18_&PRIOR_YYYYMM as p
      on c.BOOK_CD = p.BOOK_CD;
  quit;

  data _null_;
    set stg.rpt_eba_fintrep_18_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.15 then
      put "WARNING: [eba_fintrep_18] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_eba_fintrep_18_archive(period=);
  /* retained for 10 years per the group records retention schedule */
  data hist.rpt_eba_fintrep_18_&period.;
    set stg.rpt_eba_fintrep_18;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_eba_fintrep_18_var;
  quit;
%mend;
