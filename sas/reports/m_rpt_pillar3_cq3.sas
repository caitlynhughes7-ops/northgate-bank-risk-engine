/*--------------------------------------------------------------------------
  m_rpt_pillar3_cq3.sas
  Pillar 3 CQ3 - credit quality by past due days
  Output: &OUTBOUND./pillar3_cq3_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_pillar3_cq3(inds=stg.ecl_acct, period=);
  %log_step(rpt_pillar3_cq3);

  proc sql;
    create table stg.rpt_pillar3_cq3 as
    select SEGMENT, SICR_REASON,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2
    from &inds
    group by SEGMENT, SICR_REASON
    order by SEGMENT, SICR_REASON;
  quit;

  proc export data=stg.rpt_pillar3_cq3
       outfile="&OUTBOUND./pillar3_cq3_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_pillar3_cq3_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the Regulatory Reporting control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_pillar3_cq3 where EAD is null;
    select count(*) into :n_neg  from stg.rpt_pillar3_cq3 where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_pillar3_cq3;
  quit;

  %if &n_null > 0 %then %put ERROR: [pillar3_cq3] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [pillar3_cq3] &n_neg rows with negative ECL;
  %put NOTE: [pillar3_cq3] submission total ECL &tot;

  /* prior period comparison - variance over 15% is queried by Regulatory Reporting */
  proc sql;
    create table stg.rpt_pillar3_cq3_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_pillar3_cq3 as c
    left join hist.rpt_pillar3_cq3_&PRIOR_YYYYMM as p
      on c.BOOK_CD = p.BOOK_CD;
  quit;

  data _null_;
    set stg.rpt_pillar3_cq3_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.10 then
      put "WARNING: [pillar3_cq3] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_pillar3_cq3_archive(period=);
  /* retained for 6 years per the group records retention schedule */
  data hist.rpt_pillar3_cq3_&period.;
    set stg.rpt_pillar3_cq3;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_pillar3_cq3_var;
  quit;
%mend;
