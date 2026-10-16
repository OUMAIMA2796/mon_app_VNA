# Comparateur VAN — 2 Projets 📊

Application Streamlit pour comparer la **Valeur Actuelle Nette (VAN)** de deux projets.

## Lancement

```powershell
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Puis ouvrir http://localhost:8501

## Fonctionnalités

- Paramètres : taux d'actualisation, durée, investissements initiaux
- Saisie annuelle détaillée ou flux constant + croissance
- Indicateurs : VAN, TRI, Indice de Profitabilité, DRCI actualisé
- Graphiques Plotly :
  1. Barres de comparaison des VAN
  2. VAN cumulée actualisée (payback)
  3. Sensibilité VAN au taux (visualise le TRI)
  4. Cash-flows bruts vs actualisés
