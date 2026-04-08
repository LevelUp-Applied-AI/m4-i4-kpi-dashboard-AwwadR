# Executive Summary — Amman Digital Market Analytics

## Top Findings

1. The Amman Digital Market generated **48,701.50** in total revenue from **443 valid orders**, with an average order value of **109.94** after excluding cancelled orders and suspicious quantities above 100.
2. **Amman** was the top revenue-generating city, contributing noticeably more revenue than any other city in the dataset.
3. Average order value differed significantly across product categories, and **Books** had the highest average order value at about **70** per category-level order contribution.
4. Monthly performance was mostly stable through much of the analysis period, but revenue and order volume both increased sharply in the final observed month.
5. The relationship between customer city and product category was weak, and the chi-square test did not find a statistically significant association between them.

## Supporting Data

- **Finding 1** is supported by the KPI baseline summary from `analysis.py`:
  - Total revenue = **48,701.50**
  - Total valid orders = **443**
  - Average order value = **109.94**
- **Finding 2** is supported by the **Revenue by City** KPI and the chart `revenue_by_city.png`, where Amman appears as the highest-revenue city.
- **Finding 3** is supported by the **Average Order Value by Product Category** KPI and the chart `avg_order_value_by_category.png`.
  - The ANOVA test result showed a statistically significant difference across categories:
    - **F = 56.7853**
    - **p-value = 2.1069868717112423e-52**
    - **eta squared = 0.2111**
- **Finding 4** is supported by the charts `monthly_revenue.png` and `monthly_order_volume.png`, which show a generally steady pattern followed by a clear rise at the end of the period.
- **Finding 5** is supported by the chi-square test:
  - **Chi-square = 20.6990**
  - **p-value = 0.8971**
  - **Cramer's V = 0.0619**
  This indicates that customer city and product category do not appear to have a meaningful association in this dataset.

## Recommendations

1. The business should give more visibility and promotion to high-value categories, especially **Books** and **Electronics**, because category-level order value differs significantly across product groups.
2. The business should continue prioritizing **Amman** as a core market, since it contributes the highest total revenue, while also monitoring lower-performing cities for growth opportunities.
3. The business should track **monthly revenue** and **monthly order volume** together each month so managers can quickly tell whether sales changes are driven by more orders, larger order values, or both.