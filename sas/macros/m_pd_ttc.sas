/*--------------------------------------------------------------------------
  m_pd_ttc.sas
  Through-the-cycle PD by internal rating grade (logistic scorecard).
  NOTE: superseded by the PIT model in v4.2 - retained pending Model
  Governance retirement (see docs/CHANGELOG.txt). Do not delete.
--------------------------------------------------------------------------*/
%macro pd_ttc(inds=, outds=);
  %log_step(pd_ttc, msg=DEPRECATED);

  data &outds;
    set &inds;
    /* scorecard coefficients calibrated 2016, refreshed 2018 */
    _score = -4.35
             + 0.212 * RATING_GRADE
             + 0.004 * min(LTV, 150)
             + 0.310 * (ARREARS_BUCKET ne '0')
             + 0.180 * FORBEARANCE_FL;
    PD_TTC = 1 / (1 + exp(-_score));
    drop _score;
  run;
%mend;
