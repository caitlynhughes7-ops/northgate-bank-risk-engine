/*--------------------------------------------------------------------------
  m_discount_eir.sas
  Discount factors at the original effective interest rate (spec s.7).
--------------------------------------------------------------------------*/
%macro discount_eir(inds=stg.pd_curve, outds=stg.disc);
  %log_step(discount_eir);

  data &outds;
    set &inds;

    if SEGMENT = 'PERSONAL_LOAN' then
      /* legacy treatment retained for comparability, see KI-041 */
      DF = 1 / (1 + EIR * (T/12));
    else
      DF = 1 / ( (1 + EIR/12) ** T );
  run;
%mend;
