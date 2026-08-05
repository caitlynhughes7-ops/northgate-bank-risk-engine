/*--------------------------------------------------------------------------
  m_rpt_pillar3_cq1.sas
  Pillar 3 CQ1 - credit quality of forborne exposures
  Output: &OUTBOUND./pillar3_cq1_&PERIOD..csv
--------------------------------------------------------------------------*/
%macro rpt_pillar3_cq1(inds=stg.ecl_acct, period=);
  %log_step(rpt_pillar3_cq1);

  proc sql;
    create table stg.rpt_pillar3_cq1 as
    select BOOK_CD, SEGMENT,
           count(*)  as N_EXPOSURES,
           sum(EAD)  as EAD  format=comma18.2,
           sum(ECL)  as ECL  format=comma18.2,
           mean(LGD) as AVG_LGD format=percent9.2
    from &inds
    group by BOOK_CD, SEGMENT
    order by BOOK_CD, SEGMENT;
  quit;

  proc export data=stg.rpt_pillar3_cq1
       outfile="&OUTBOUND./pillar3_cq1_&period..csv"
       dbms=csv replace;
  run;
%mend;

%macro rpt_pillar3_cq1_validate(period=);
  /* control totals circulated with the submission - do not remove, these are
     referenced in the the CFO's office control attestation                          */
  %local n_null n_neg tot;
  proc sql noprint;
    select count(*) into :n_null from stg.rpt_pillar3_cq1 where EAD is null;
    select count(*) into :n_neg  from stg.rpt_pillar3_cq1 where ECL < 0;
    select sum(ECL) into :tot    from stg.rpt_pillar3_cq1;
  quit;

  %if &n_null > 0 %then %put ERROR: [pillar3_cq1] &n_null rows with null EAD;
  %if &n_neg  > 0 %then %put ERROR: [pillar3_cq1] &n_neg rows with negative ECL;
  %put NOTE: [pillar3_cq1] submission total ECL &tot;

  /* prior period comparison - variance over 15% is queried by the CFO's office */
  proc sql;
    create table stg.rpt_pillar3_cq1_var as
    select c.*, p.ECL as ECL_PRIOR,
           case when p.ECL > 0 then (c.ECL - p.ECL) / p.ECL else . end
             as VAR_PCT format=percent9.2
    from stg.rpt_pillar3_cq1 as c
    left join hist.rpt_pillar3_cq1_&PRIOR_YYYYMM as p
      on c.SEGMENT = p.SEGMENT and c.STAGE = p.STAGE;
  quit;

  data _null_;
    set stg.rpt_pillar3_cq1_var;
    if not missing(VAR_PCT) and abs(VAR_PCT) > 0.10 then
      put "WARNING: [pillar3_cq1] variance " VAR_PCT percent9.2 " exceeds tolerance";
  run;
%mend;

%macro rpt_pillar3_cq1_archive(period=);
  /* retained for 10 years per the group records retention schedule */
  data hist.rpt_pillar3_cq1_&period.;
    set stg.rpt_pillar3_cq1;
    RUN_DTTM = datetime();
    RUN_ENV  = "&ENV";
    format RUN_DTTM datetime20.;
  run;

  proc datasets library=stg nolist;
    delete rpt_pillar3_cq1_var;
  quit;
%mend;
