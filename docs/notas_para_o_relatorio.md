# Notas para o relatório

Material de apoio para atualizar `analise-residuos-sinisa.docx` se o grupo quiser. **O relatório não foi alterado.** Os números que ele já traz (4.854 municípios, IRS0001 = 81,65%, IRS3002 = 33,87%, SP = 6,71% simples e 7,89% ponderada, 20ª posição de 27) continuam corretos e são conferidos por testes automatizados.

## Texto sugerido: como interpretar os zeros do IRS3002 (seção 2.2)
> A disposição final inadequada (IRS3002) concentra-se em dois valores: 63% dos municípios respondentes registram 0% e 31%, 100%. O indicador é calculado pelo SINISA a partir das rotas de coleta declaradas por cada município, cada uma com o tipo de unidade de destino; a massa das rotas que vão a lixão, vazadouro ou aterro controlado, dividida pela massa coletada líquida, reproduz o indicador publicado em todos os 4.854 municípios (diferença máxima de 0,005 ponto percentual). Assim, um valor de 0% significa que o município não declarou nenhuma rota para esses destinos. Entre os 3.057 municípios com 0%, 94% declararam rotas a aterro sanitário ou de inertes que cobrem ao menos 90% da massa coletada líquida; 6% completam a massa somando unidades intermediárias (transbordo, triagem, compostagem), sem informar o destino final dos rejeitos; e 3 municípios têm declaração incompleta. Nenhum município com 0% declarou rota para lixão ou aterro controlado. Como os dados são autodeclarados, os resultados mostram o que os municípios informaram ao SINISA, não o que foi verificado em campo.

## Texto sugerido: engenharia de dados (seção 2.1)
> O processo de ETL foi automatizado e testado: a carga é montada em arquivo temporário e só substitui o banco depois de passar na validação; o banco gerado é idêntico byte a byte a cada execução com as mesmas entradas; e o ETL confere o IRS3002 contra as rotas de coleta antes de aceitar a carga. O projeto conta com 74 testes automatizados e integração contínua no GitHub.

## O que mudou no projeto (resumo para a apresentação)
- Os zeros do IRS3002 deixaram de ser "pode ser informação não preenchida" e passaram a ter explicação baseada nos dados.
- O ETL ficou mais seguro (carga atômica), mais rápido quando nada mudou (2 s contra 21 s) e passou a conferir o indicador.
- Cálculos do dashboard, da análise e da planilha agora vêm do mesmo módulo (`scripts/calculos.py`), então os números não divergem.
- O limite de 3 kg/hab.dia para sinalizar massa per capita foi justificado nos dados: fica logo acima do percentil 99 (3,13) e perto da cerca de Tukey para valores extremos (2,98). Sinaliza 59 municípios (1,2%).

## Erros de interpretação que o próprio processo pegou (útil para a seção de qualidade)
Duas versões da análise dos zeros foram descartadas por auditoria independente antes de chegar ao dashboard final: a primeira lia a planilha errada (unidades sediadas no município) e a segunda usava os fluxos declarados pelo município receptor. Só a terceira reproduz o indicador. A lição, aplicada ao ETL: antes de interpretar um indicador, reproduza-o a partir da fonte; se não reproduz, a fonte está errada.
