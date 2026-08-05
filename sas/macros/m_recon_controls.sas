/*--------------------------------------------------------------------------
  m_recon_controls.sas
  Post run controls (spec s.8). Tolerance widened in v4.7.
--------------------------------------------------------------------------*/
%macro recon_controls(tapeds=stg.tape_arrears, eclds=stg.ecl_acct);
  %log_step(recon_controls);

  proc sql noprint;
    select sum(DRAWN_BAL) into :tape_drawn from &tapeds;
    select sum(EAD), sum(ECL) into :ecl_ead, :ecl_tot from &eclds;
    select count(*) into :n_nullstage from &eclds where STAGE is null;
  quit;

  %put NOTE: [ECL] control drawn=&tape_drawn ead=&ecl_ead ecl=&ecl_tot;

  %if &n_nullstage > 0 %then %do;
    %put ERROR: [ECL] &n_nullstage exposures with null stage;
  %end;
%mend;
