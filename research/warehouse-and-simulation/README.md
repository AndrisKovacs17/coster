# Warehouse and simulation

Automated storage (AS/RS) and warehouse simulation, storage assignment rules, digital twins, and
analog problems where part of the future is scheduled, for example hospital bed occupancy with
planned admissions.

| Source | Type | Status | Note |
|---|---|---|---|
| Roodbergen and Vis 2009, AS/RS survey (`roodbergen2009asrs`), [DOI](https://doi.org/10.1016/j.ejor.2008.01.038) | Review | to read | Standard AS/RS review: configuration, storage assignment, sequencing. Notes that most models are static. |
| Bertolini et al. 2023, AS/RS literature 2009–2019 (`bertolini2023asrs`), [DOI](https://doi.org/10.1504/IJLSM.2023.130783) | Review | to read | Follow-up to Roodbergen and Vis, more than 1,000 Scopus papers. Search it for occupancy and saturation work. |
| Gu et al. 2007, warehouse operation review (`gu2007warehouse`), [DOI](https://doi.org/10.1016/j.ejor.2006.02.025) | Review | to read | Receiving, storage, picking, shipping. Companion: Gu et al. 2010 on design and performance (`gu2010warehousedesign`). |
| Hausman et al. 1976, storage assignment in automated warehouses (`hausman1976storage`), [DOI](https://doi.org/10.1287/mnsc.22.6.629) | Paper | to read | Origin of class-based storage. Background for "smallest cell that fits". |
| Boysen et al. 2019, warehousing in the e-commerce era (`boysen2019ecommerce`), [DOI](https://doi.org/10.1016/j.ejor.2018.08.023) | Review | to read | Recent automated systems overview |
| Optimal design of rack structure with modular cell in AS/RS, IJPE 98(2) 2005, [IAOR](https://www.iaorifors.com/paper/49886) | Paper | to read | Racks with cells of different sizes, like the 5 AW classes. Authors not yet recorded. |
| Kuhl et al. 2022, Warehouse digital twin (`kuhl2022warehousedt`), [WSC PDF](https://www.informs-sim.org/wsc22papers/297.pdf) | Paper, open | to read | How a twin is synchronised with the real system. Our flow balance is a minimal twin. |
| Takeda-Berger and Frazzon 2024, inventory data-driven predictive-reactive scheduling (`takedaberger2024inventory`) | Paper | to read | Inventory under machine breakdowns, the uncertainty Coster raised on 16 Oct |
| Littig and Isken 2007, short-term hospital occupancy prediction (`littig2007occupancy`), [DOI](https://doi.org/10.1007/s10729-006-9000-9) | Paper | to read | **Closest analog.** Occupancy built from scheduled admissions plus predicted stays. Same structure as plans plus flow balance. |
| Bekker and Koeleman 2011, scheduling admissions and bed demand variability (`bekker2011admissions`), [DOI](https://doi.org/10.1007/s10729-011-9163-x) | Paper | to read | Infinite-server queue (G/G/∞) view of occupancy from scheduled arrivals. Analytic alternative to Monte Carlo. |
| Shah et al. 2021, NHS non-elective bed forecasting (`shah2021nhsbeds`), [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8517824/) | Paper, open | to read | Exponential smoothing beat other methods over 4 weeks (median error 4.91%). Shows how strong a plain baseline can be. |
| Tavafoghi et al. 2019, queuing approach to parking (`tavafoghi2019parking`), [arXiv 1908.11479](https://arxiv.org/abs/1908.11479) | Paper, open | to read | Probabilistic occupancy forecast for a capacity-limited lot. Compared model-based and model-free methods. |
| Container yard dwell-time prediction, [arXiv 2602.20540](https://arxiv.org/abs/2602.20540); empty container availability, [arXiv 2503.11728](https://arxiv.org/abs/2503.11728) | Papers, open | to read | Port yards as a capacity analog. LSTM beat ARIMA and Prophet in the second. |
