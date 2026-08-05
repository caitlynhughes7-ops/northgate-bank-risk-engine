/*--------------------------------------------------------------------------
  m_rpt_eba_fintrep_19.sas
  EBA FINREP F19 - forbearance
  Output: &OUTBOUND./eba_fintrep_19_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_eba_fintrep_19(inds=stg.ecl_acct, period=);
  %log_step(rpt_eba_fintrep_19);

  proc sql;
    create table stg.rpt_eba_fintrep_19 as
    select SEGMENT, STAGE,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    where STAGE in (2,3)
    group by SEGMENT, STAGE
    order by SEGMENT, STAGE;
  quit;

  proc export data=stg.rpt_eba_fintrep_19
       outfile="&OUTBOUND./eba_fintrep_19_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_eba_fintrep_19_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the the CFO's office control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_eba_fintrep_19 where EAD is null;
    select count(*) into :n_neg  from stg.rpt_eba_fintrep_19 where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_eba_fintrep_19;
  quit;

  %if &n_null > 0 %then %put ERROR: [eba_fintrep_19] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [eba_fintrep_19] &n_neg rows with negative ECL;
  %put NOTE: [eba_fintrep_19] submission total ECL &tot;

  /* prior period comparison - variance over 5% is queried by the CFO's office */
  proc sql;
    create table stg.rpt_eba_fintrep_19_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_eba_fintrep_19 as c
    left join hist.rpt_eba_fintrep_19_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT;
  quit;

  data _null_;
    set stg.rpt_eba_fintrep_19_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.05 then
      put "WARNING: [eba_fintrep_19] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_eba_fintrep_19_archive(period=);
  /* retained for 7 years per the group records retention schedule */
  data hist.rpt_eba_fintrep_19_&period.;
    set stg.rpt_eba_fintrep_19;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_eba_fintrep_19_var;
  quit;
%mend;
