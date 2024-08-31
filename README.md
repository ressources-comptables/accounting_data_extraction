# Présentation de la base de données

La base de données comprend les tables qui doivent être remplis manuellement avant le traitement des texte et des tables qui seront remplis automatiquement lors de traitement automatisé. Les tables qui seront remplis automatiquement doivent également être vérifier et corriger si nécaissaire.
Ci-après il suit la description de toutes les étapes de traitement des textes.

## Notes

### Table "user"

Table "user" est uniquement pour les comptes des utilisateurs du site web du projet. Cette table n'est donc pas relié aux données comptables et peut être aisement suprimé de la base de donnée.


### Tables des traductions

Ces tables ne sont pas pour l'heure utilisées, mais peuvent être utilisées dans le cadre de "l'internalisation" des données:

  - product_translation
  - person_role_translation

A noter que certaines d'autres tables de traduction sont utilisées. Cela est par exemple le cas pour les traductions des noms des rubriques et sous-rubriques et noms des monnaies. De fais, les noms des rubriques, des sous-rubriques et des monnaies sera affiché sur le siteweb et dans les analyses statistiques, leur traductions a été alors nécaissaire.

De l'autre coté, l'extraction des noms des produits a été peu précise et leur traductions a été alors délicate. La traduction des "rôle" des personnes est aussi délicate du à différente tradition historiographique et l'ambiguité de certains termes; la décision a été alors prise de garder les noms des "rôles" originale.

# Etapes de traitement

## Etape 0: Remplissage manuelle préalable

Cette étape ne doit être réalisé qu'une seule fois au tout début avant le premier traitement automatique.

Vous pouvez utilisé la base de donnée prérempli disponible ici. Il faudra seulement y ajouter vos informations sur les documents (tables: corpus, documents, corpus_content, emission).

Les tables suivantes doivent être remplies manuellement:

### Documents

Table "corpus" - avec les noms des corpus. (il faut avoir au moins un corpus dans la base)

Table "document" - avec les noms des documents (comptes). (il faut avoir au moins un document dans la base) (ajouter également les dates (start_date_standardized) pour chaque document)

Table "corpus_content" - relier manuellement les documents aux corpus auxquels ils appartienent

Table "emission" - relier le document avec son émitteur (auteur). (il faut alors avoir au moins un personne dans la base qui sera l'emitteur de document.)

### Classification du text

transaction_class - class de transaction (1 - expense, 2 - revenue)

line_type - type de ligne. On peut avoir les types suivants:
  1	Description
  2	Transaction
  3	RubricName
  4	SubrubricName
  5	SumUndefined
  6	SumPage
  7	SumRubric
  8	SumPeriod
  9	SumTotal

### Monnaies

currency_standardized - les noms des monnaies. Ne pas changer les noms des monnaies une fois le traitement des textes a commencé, car lors de traitement des textes on attribute automatiquement les id des monnaies aux montants extraits. Si on change les id des monnaies une fois que l'on a déjà traité une partie des textes, on se retrouvera alors avec les ids des monnaies difféerents entre les différents texte. (Sinon, il faudra mettre en place un post-traitement que reverifiera les noms des monnnaies attribés à chaque montant.)

currency_variant - la même chose que pour currency_standardized. Ne pas changer après le début du traitement automatique (sinon il faudra mettre en place un post-traitement supplémentaire pour reverifier les noms des monnnaies attribés à chaque montant) 

currency_translation - les traductions (français, anglais, etc.) des noms des monnaies.

unit_of_count - ne pas changer. Les ids de change unité sont inscrit "en dur" dans le code python de traitement automatisé. L'ordre doit respecter l'ordre hiérarchique "naturel" des valeurs des unités (de plus grande vers la plus petite). Les unités de comptes possibles: 
  1	libra	lb.
  2	solidus	s.
  3	denarius	d.
  4	obolus	ob.
  5	picta	p.
  6	maille	m.

### Personne

person_function - les fonctions de la personne. Deux valeurs: 1 - beneficiary, 2 - payer

person_type - type de personne. Deux valeurs: 1 - natural person, 2 - legal person


## Etape 1: Traitement principale automatique

On configure la connexion à la base sql dans main.py

Pour chaque texte on change file_name, document_id et, si nécaissaire, class_id dans main.py

On lance main.py

Lors de traitement autoamtique du texte, ces tables seront remplies automatiquement:

rubric_extracted
rubric_standardized
subrubric_extracted
subrubric_standardized
line
amount_composite
amount_simple
date
product
participant (tous les champs sauf person_id. person_id sera inserer automatiquement lors de post-traitement)
exchange_rate_internal_reference (uniquement le champ exchange_rate_extracted)

### Ajouter des nouveaux texte

On ajoute ainsi chaque texte en changeant le nom du fichier et l'id du document dans main.py
On peut procéder de deux façons:
1. Soit d'abord charger tous les textes et ensuite procéder à la vérification manuelle et au post-traitement de l'ensemble des textes;
2. Soit travailler texte par texte (chargement du texte dans la base, vérification manuelle, post-traitement).
Les deux approches peuvent être utilisées.

Les nouveaux textes peuvent par la suite être ajouter dans la basé de la même façon:
1. Traitement principal automatique (on met le nom du fichier et l'id du document dans main.py)
2. Vérification manuelle du texte ajouté.
3. Post-traitement du texte ajouté.
4. Vérification manuelle du post-traitement.



## Etape 2: Vérification manuelle après le traitement automatique

Toutes les tables remplis automatiquement lors de la phase de traitement automatique doivent être vérifier manuellement.

**PENSEZ À CHAQUE FOIS DE REMPLACE DANS LES REQUETTE SQL ICI PRÉSENT LE NUMÉRO DE DOCUMENT PAR LE DOCUMENT SUR LEQUEL VOUS TRAVAILLEZ**

### Etape 2.1 Vérification de l'ensemble (sauf product, particpant, montant)

Après le traitement automatique on commence par vérifier les lignes extraites et quelques données qui y sont associé.
On prend uniquement les données qui peuvent être présent en une seule entité par une ligne donnée. Par exemple, une ligne peut avoir un seul type de ligne, ou une seule date de début. De fait, si on prend les données qui peuvent être présent à plusieurs entités (par exemple une ligne peut avoir plusieurs montants), cela multipliera le nombre de ligne (chaque ligne sera affiché autant de nombre de fois que le nombre d'exemeplaire d'entité donnée). Or, on souhaite avoir le premier apperçu générale des données extraites avec des lignes "uniques" pour se faire une première idée. Pour cette raison, on évite les données qui peuvent avoir de plusieurs instances; ces données seront vérifier après.

```
SELECT
	l.document_id,
	l.line_id,
	l.line_number,
	l.folio,
	l.text,
	lt.line_type_id,
	lt.line_type_name,
	re.rubric_name_extracted,
	rs.rubric_name_standardized,
	sre.subrubric_name_extracted,
	srs.subrubric_name_standardized,
	d.start_date_extracted,
	d.start_date_standardized,
	d.date_id,
	d.start_date_uncertainty,
	d.end_date_extracted,
	d.end_date_standardized,
	d.end_date_uncertainty,
	d.duration_extracted,
	d.duration_standardized_in_days,
	d.duration_uncertainty
FROM
	line l
	LEFT JOIN line_type lt ON l.line_type_id = lt.line_type_id
	LEFT JOIN rubric_extracted re ON l.rubric_extracted_id = re.rubric_extracted_id
	LEFT JOIN rubric_standardized rs ON re.rubric_standardized_id = rs.rubric_standardized_id
	LEFT JOIN subrubric_extracted sre ON l.subrubric_extracted_id = sre.subrubric_extracted_id
	LEFT JOIN subrubric_standardized srs ON sre.subrubric_standardized_id = srs.subrubric_standardized_id
	LEFT JOIN date d ON l.date_id = d.date_id
WHERE
	l.document_id = 1;
```

Cette requette permet de produire un tableau générale avec les données principales associés à une ligne.
Le resultat de cette requette peut être exporté pour la vérification sous format csv (pour ouvrir avec Excel) ou tout un autre format ou bien étudier directement dans l'éditeur de SQL.
L'objectif est d'avoir le premier apperçu des principaux données extraites. Si les données doivent être corrigées, il faudra aller dans la table correspondante de ces données et de les corriger.

Ce que l'on vérifie:

#### 2.1.1 Types de ligne

On regarde que les types de ligne (description, transaction, les différentes sommes, etc.) ont été bien identifés.

On vérifie notamment si tous **les sommes de rubriques** et **la somme totale à la fin du compte** ont été bien idenitifé. On regarde également les **SumUndefined**. Pour simplifier le changement on peut ouvrir directement la table "line".

Ensuite on vérifie si toutes **les lignes avec les Transactions** ont été bien identifié (souvent cela n'est pas le cas, car il n'y a pas toujours un schéma fixe de la présentation des montants dans la ligne). Pour cela, dans le resultat de requette précédente on prendre uniquement **les lignes "Description"** et on vérifie le texte de ces lignes. S'il faut changer le type de ligne de "Description" vers "Transcription" on utilise en parallèle la table "line".

On peut utiliser ce code pour changer les types de lignes (on part du principe que le type de ligne "Transaction" est line_type_id = 2):
(changez les line_id par les votres)

```
UPDATE `line`
SET `line_type_id` = 2
WHERE `line_id` IN (23, 49, 50, 51, 52, 53, 89, 490, 2008);
```


#### 2.1.2 Ajout des taux de change supplémentaire

Lors de la vérification des lignes d'un compte, il n'est pas rare que l'on peut s'appercevoir qu'il y a des lignes qui contiennent des taux de changes mais qui n'ont pas été identifé lors de traitement automatique. Dans ces cas-là, on peut inserer ces lignes manuellements dans la table "exchange_rate_internal_reference".
Pour cela, il faut noter les id de ces lignes (line_id) et ensuite il est possible soit les insérer manuellement, soit utiliser ce code sql:

1. Vérifier les lines qui contient les taux de change.

(cette vérification peut être utile, mais absolument pas nécaissaire)
(les numéros des lignes sont données pour l'exemple; changez les numéros des lignes)

````
SELECT line_id, text
FROM line
WHERE line_id IN (23, 49, 50, 51, 52, 53, 89, 490, 2008);
````

2. Insérez des lignes dans exchange_rate_internal_reference si elles n'existent pas déjà.

(changez les numéros des lignes)

```
INSERT INTO exchange_rate_internal_reference (line_id, exchange_rate_extracted)
SELECT l.line_id, l.text
FROM line l
LEFT JOIN exchange_rate_internal_reference er ON l.line_id = er.line_id
WHERE l.line_id IN (23, 49, 50, 51, 52, 53, 89, 490, 2008)
  AND er.line_id IS NULL
```



#### 2.1.3 Dates

**Start dates (date de début)**

Le regard particulier doit être porté aux données liées aux dates (dates début et fin et la durée). Ces données doivent être vérifier et corriger à ce stade.

On vérifie les dates pour chaque document avec ce code:

```
SELECT
	l.document_id,
	l.line_id,
	l.text,
	d.start_date_extracted,
	d.start_date_standardized,
	d.date_id
FROM
	line l
	LEFT JOIN date d ON l.date_id = d.date_id
WHERE
	l.document_id = 1
```

On note toutes les date_id à corriger et les "bonnes" années.
Ensuite on peut utiliser ce code pour mettre à jour les données dans la base sql (à faire "année par année"):

```
UPDATE `date`
SET `start_date_standardized` = CONCAT('1330-', DATE_FORMAT(`start_date_standardized`, '%m-%d'))
WHERE `date_id` IN (34, 45, 55, 67, 68, 69, 70, 71, 87)
```

(faire ce code pour chaque année à changer)

**End dates (date de fin)**

Il faut égalemet mettre à jours (changer l'année) pour les dates de fin en fonction des nouvelles années des dates de début (changé précédement).
Il faut alors cela: pour toutes les lignes où end_date_standardized n'est pas vide
si la valeur de end_date_standardized est inférieure à la valeur de start_date_standardized, changez l'année dans end_date_standardized par l'année à partir de start_date_standardized
Pour cela on va utiliser ce code:

```
UPDATE date
SET end_date_standardized = DATE_FORMAT(CONCAT(YEAR(start_date_standardized), '-', MONTH(end_date_standardized), '-', DAY(end_date_standardized)), '%Y-%m-%d')
WHERE end_date_standardized IS NOT NULL
AND end_date_standardized < start_date_standardized;

```

#### 2.1.4 Traitement automatique supplémentaire des nouvelles lignes "transactions"

Après l'identification manuelle des lignes suppléementaires "Transactions" (il s'agit des lignes qui ont échappé au premier traitement automatique), il faut traiter de nouveau ces nouvelles lignes identifiés. Ce traitement consiste uniquement l'identification des montants présents dans ces nouvelles lignes. 
**Pour cela, il suffit de lancer le script "postprocessing_1_new_transactions.py".**


### Etape 2.2 Rubriques et sous-rubriques

La prochaine étape est la vérification plus détaillé des noms des rubriques et des sous-rubriques.
Même si le premier regard à ces données a été déjà fait grace à la requette précédente, il est indispensable de vérifier ces données de plus près. 
De fait, les noms des rubriques et des sous-rubriques peuvent être partagés par les différents textes. 
Pour cette raison, il faut les vérifier après l'ajout de chaque nouveau text.
Les traductions des rubriques et des sous-rubriques doivent (si nécaissaire) également être ajouté manuellement à ce stade.

rubric_standardized - verifier manuellement les noms "standardisés" des rubriques
rubric_translation - faire manuellement la traduction des noms des rubrics standardisés
subrubric_standardized - verifier manuellement les noms "standardisés" des sous-rubriques
subrubric_translation - faire manuellement la traduction des noms des sous-rubrics standardisés

On peut utiliser ce code:

```

SELECT
	rubric_extracted.rubric_extracted_id,
	rubric_extracted.rubric_name_extracted,
	rubric_standardized.rubric_name_standardized,
	rubric_standardized.rubric_standardized_id
FROM rubric_extracted
JOIN rubric_standardized ON rubric_extracted.rubric_standardized_id = rubric_standardized.rubric_standardized_id

```


### Etape 2.3 Product

Le taux de précision de l'extraction des "produit" est assez bas (56% environ), donc il n'y a pas grande chose à faire pour modifier ou améliorer l'extraction des "produits". On peut toutefois, rapidement examiner les données qui ont été extraites.

La requette à utiliser:

````
SELECT 
    l.document_id,
    l.line_id,
    l.line_number,
    l.folio,
    l.text,
    p.product_extracted,
    p.product_uncertainty
FROM 
    line l
LEFT JOIN 
    product p ON l.line_id = p.line_id
WHERE 
    l.document_id = 1
````

Après l'insertion automatique des données, le colonne "product_extracted" contient des grands textes. Alors, on va couper  le contenu de cette colonne pour que cela ne dépasse pas 100 mots et rajouter [...] à la place du texte coupé.
Voici le code à utiliser:

```
UPDATE product
SET product_extracted = CONCAT(
  SUBSTRING_INDEX(product_extracted, ' ', 100),
  ' [...]'
)
WHERE CHAR_LENGTH(product_extracted) > CHAR_LENGTH(SUBSTRING_INDEX(product_extracted, ' ', 100))
```


### Etape 2.4 Participant

Cette requette permet d'avoir le premier regard sur les participants extraits depuis le texte. 
Lors de cette étape on fait le nettoyage suivant dans la table "participant":

- la colonne "participant_name_extracted" - ne pas changer les noms eux-mêmes (on garde les originaux pour pouvoir les restituter si nécaissaire), mais supprimer les données mal identifés (les "non-noms", les mots inutiles, etc.);
- la colonne "participant_role_extracted" - le même type de nettoyage que précédement, on ne change pas le role "original" (on garde les originaux au cas où), mais on supprime les données mal identifiées (les "non-roles", les mots inutiles, etc).
- la colonne "participant_group" - s'il y a des groupes de personne de type "XVI capellanis" on ajoute "1" (=yes) dans la colonne "participant_group" et on présente les données comme suit:
participant_name_extracted / participant_role_extracted / participant_group
XVI capellanis / capellanus / 1 


A noter que l'on ne travaille pas encore avec les "personnes" car les personnes seront construite lors de post-traitement à partir de ces noms extraits.

```
SELECT
	line.document_id,
	line.line_id,
	line.line_number,
	line.folio,
	line.TEXT,
	participant.participant_id,
	participant.participant_extracted,
	participant.participant_name_extracted,
	participant.participant_role_extracted,
	participant.additional_participant,
	participant.participant_uncertainty,
	person_function.person_function_name 
FROM
	line
	JOIN participant ON line.line_id = participant.line_id
	JOIN person_function ON participant.person_function_id = person_function.person_function_id 
WHERE
	line.document_id = 1
```

A noter que le deuxième traitement automatique (voir plus bas) produira les noms des personnes standardisé (table "person") et les roles standardisé (table "person_role"). Donc les noms standardisés des personnes seront ensuite préciser dans la table "person" et les roles standardisés seront préciser dans la table "person_role". Il faut se rappeler de cela! C'est à dire que dans la table "participant" on ne "standardise" pas ni les noms ni les roles; on garde dans la table "participant" les noms et les roles "originaux" comme ils sont présent dans le texte (dans l'eventualité pouvoir les restituer ou consulter après.)

Parfois, participant_name_extracted et participant_role_extracted peuvent avoir un espace au début et à la fin du text, on peut trouver ces texte comme cela:

```
SELECT
  participant_id,
  participant_name_extracted,
  participant_role_extracted
FROM participant
WHERE
  BINARY participant_name_extracted != BINARY TRIM(participant_name_extracted)
  OR BINARY participant_role_extracted != BINARY TRIM(participant_role_extracted)
```

On peut ensuite, s'il y en a, supprimer ces espaces au début et à la fin du contenu des participant_name_extracted et participant_role_extracted:

```
UPDATE participant
SET
  participant_name_extracted = TRIM(participant_name_extracted),
  participant_role_extracted = TRIM(participant_role_extracted)
```

Après tout le nettoyage, on peut vérifier le contenu des participant_name_extracted et participant_role_extracted pour peaufiner: 

pour participant_name_extracted

```
SELECT
	DISTINCT participant_name_extracted,
	COUNT(*) AS number
FROM 
	participant
GROUP BY
	participant_name_extracted
```

pour participant_role_extracted

```
 SELECT
	DISTINCT participant_role_extracted,
	COUNT(*) AS number
FROM
	participant
GROUP BY
	participant_role_extracted
```



### Etape 2.5 Montants

Pour vérifier les montants "composites:

```
SELECT
	ac.line_id,
	ac.amount_composite_id,
	ac.amount_composite_extracted,
	asimple.amount_simple_id,
	asimple.amount_simple_extracted,
	asimple.currency_extracted,
	cs.currency_name,
	asimple.arithmetic_operator,
	ass.amount_simple_subpart_id,
	ass.subpart_extracted,
	ass.roman_numeral,
	ass.arabic_numeral,
	uoc.unit_of_count_name 
FROM
	amount_composite ac
	LEFT JOIN amount_simple asimple ON ac.amount_composite_id = asimple.amount_composite_id
	LEFT JOIN amount_simple_subpart ass ON asimple.amount_simple_id = ass.amount_simple_id
	LEFT JOIN currency_standardized cs ON asimple.currency_standardized_id = cs.currency_standardized_id
	LEFT JOIN unit_of_count uoc ON ass.unit_of_count_id = uoc.unit_of_count_id 
WHERE
	ac.line_id IN ( SELECT line_id FROM line WHERE document_id = 1 )
```

Pour vérifier les montants "simples:

```
SELECT
	asimple.line_id,
	asimple.amount_simple_id,
	asimple.amount_simple_extracted,
	asimple.currency_extracted,
	cs.currency_name,
	asimple.arithmetic_operator,
	ass.amount_simple_subpart_id,
	ass.subpart_extracted,
	ass.roman_numeral,
	ass.arabic_numeral,
	uoc.unit_of_count_name 
FROM
	amount_simple asimple
	LEFT JOIN amount_simple_subpart ass ON asimple.amount_simple_id = ass.amount_simple_id
	LEFT JOIN currency_standardized cs ON asimple.currency_standardized_id = cs.currency_standardized_id
	LEFT JOIN unit_of_count uoc ON ass.unit_of_count_id = uoc.unit_of_count_id 
WHERE
	asimple.line_id IN ( SELECT line_id FROM line WHERE document_id = 1 )
```

Tout particulierement il faut vérifier la bonne extraction et reconnaissance des noms des monnaies.

```
SELECT DISTINCT
	currency_extracted,
	currency_standardized_id 
FROM
	amount_simple
```

Etapes de vérification:
(si nécaissaire, vérifier que les clés étrangeers dans les tables amount_composite, amount_simple et amount_simple_subpart sont mis "ON DELETE: cascade". Cela permettra la supprésion automatique les différentes données reliées à travers ces tables lors du nettoyage des données.)

1. Dans la table *amount_composite*, dans la colonne *amount_composite_extracted*:
- chercher le texte LIKE "saumata" - supprimer les inutiles;
- amount_composite_extracted LIKE '%saumat.%'
- chercher LIKE "diebus" - supprimer les inutiles;
- amount_composite_extracted LIKE '%emina%'

Il ne faut pas passer beaucoup du temps à nettoyer la table amount_composite, car le contenu de la colonne amount_composite_extracted ne s'affiche nul part. S'il y a des problèmes, on les verra bien dans la table amount_simple.

2. Dans la table *amount_simple*, dans la colonne *amount_simple_extracted*:
- chercher LIKE "diebus" - supprimer les inutiles;
- chercher LIKE "die" - supprimer les inutiles;
- chercher LIKE "saumat" - supprimer les inutiles;
- amount_simple_extracted LIKE '%servient%' - supprimer les inutiles;
- amount_simple_extracted LIKE '%septim%'
- amount_simple_extracted LIKE '%servit%'

3. Dans la table *amount_simple* on vérifie cela:
- (currency_extracted IS NULL) AND (currency_standardized_id IS NULL) - on supprime les lignes inutiles;
- (currency_extracted IS NOT NULL) AND (currency_standardized_id IS NULL) - on supprime les lignes inutiles;
- (currency_extracted IS NOT NULL) AND (currency_standardized_id IS NOT NULL) et on tri par l'ordre alphabétique ASC la colonne currency_extracted - on vérifie toutes les lignes;

(A noter. Le contenu lui-même des colonnes amount_simple_extracted et currency_extracted n'est pas important. Le contenu de ces colonnes ne s'affiche nul part, mais il est uniquement utiliser pour identifer les chiffres romains/arabes et les devises. Donc, ce n'est pas la peine de nettoyer le contenu même de ce colonne. Essentiel est de regarder si les devises sont bien identifiés dans la colonne currency_standardized_id)

4. Dans la table *amount_simple_subpart* on vérifie cela:
- vérifier si nécaissaire que les chiffres romains ont été correctement convert vers les chiffres arabes (voir notamment la spécificité des numéros du Moyen Age tardive, avec les lettres M et C placé à la fin et qui signifient qu'il faut faire une mulitplication. Par exemple: CCXLVM = 245000)


### Etape 2.6 Taux de change

Les étapes du travail:

1. Dans la table **exchange_rate_internal_reference**:

- on regarde le texte de la colonne exchange_rate_extracted pour determiner s'il contient ou non le taux de change. S'il ne contient pas le taux de change, on le supprime. S'il contient le taux de change on passe à l'étape suivante.

2. Dans la table **amount_simple**:

 - on prepare la table pour le travail, pour cela on fait ceci: 
	- on choisi les lignes qui ne concerne que les taux de changes. Pour cela on choisi les lignes où `(amount_composite_id IS NULL) AND (line_id IS NULL)`
	- on tri currency_standardized_id dans l'ordre ASC (pour ranger l'affichage par les devises)
	- on trie amount_simple_extracted par l'ordre ASC (pour ranger l'affichage dans, plus ou moins, l'orde de croissance des montants de change - à noter que cela ne marche pas toujours)

3. Maintenant on commence le travail selon ce schéma:
 - si la colonne exchange_rate_extracted de la table **exchange_rate_internal_reference** contient le taux de change d'une "1 monnaie A" vers "Montant monnaie B"
 - on vérifie dans la table **amount_simple** dans les colonnes amount_simple_extracted et currency_extracted que "Montant monnaie B" n'existe pas déja.
 - si il n'existe pas on le crée et note amount_simple_id, s'il existe déjà on note directement amount_simple_id.
 - on va dans la table **exchange_rate** et on vérifie si la paire *"1 monnaie A" vers "Montant monnaie B"* (on la répére grace à amount_simple_id) existe déjà.
 - s'il n'existe pas, on le crée (en utilisant amount_simple_id qui on a noté précédement) et on note exchange_rate_id, s'il existe on note directement exchange_rate_id.
 - on va dans la table **exchange_rate_internal_reference** et dans la colonne exchange_rate_id on saisie exchange_rate_id que on a noté.

Si le taux de change mentionné dans le texte contient une erreur (par exemple, on constate que le copiste s'est trompé et a écrit VIII s. au lieu de XVIII s.) on met dans la colonne *exchange_rate_manuscript_error* de table **exchange_rate_internal_reference**  le chiffre "1". (il faut que cela soit "1", sinon cela ne marche pas!)

Si on a des doutes sur le taux de change, on met "A vérifier" (ou toute autre note ou remarque que l'on souhaite) dans la colonne *exchange_rate_remarks* de la table **exchange_rate**.

On répete l'étape 3 pour chaque taux de change trouvé dans le texte de la colonne exchange_rate_extracted de la table **exchange_rate_internal_reference** .

Si par la suite, on souhaite d'ajouter les taux de changes connue d'apèrs d'autres sources ou la bibliographie (donc qui ne sont pas liés aux comptes de cette base de données et ne peuvant pas, par conséquent, être attaché à la table **exchange_rate_internal_reference**, on peut utiliser la table exchange_rate_date où on lie directement une date à chaque taux de change. De fait, sinon les datations des taux de changes sont calculé à travers la table exchange_rate_internal_reference).

**ATTENTION!** Ne pas changer directement les montants des taux de changes déjà saisies dans la table **amount_simple**! De fait, il y a plusieurs différents taux de change qui peuvent être attaché au même montant de taux de change saisie dans la table **amount_simple**. Par exemple, si on a le montant "*montant X monnaie B*" dans la table amount_simple, on peut avoir les taux de changes suivant attachés à ce montant: "*1 monnaie A*" - "*montant X monnaie B*" // "*1 monnaie C*" - "*montant X monnaie B*" // "*1 monnaie D*" - "*montant X monnaie B*", etc. Donc, si on change le "*montant X monnaie B*" cela affectera tous ces taux de change. Donc, il faut faire vraiment très attention. Si on veut apporter des modications dans un taux de change, il faut le faire un par un en regardant le contenu de exchange_rate_id dans la table **exchange_rate_internal_reference**.

Enfin, pour avoir un regard rapide sur les taux de changes existants:

```
SELECT
	er.exchange_rate_id,
	cs.currency_name,
	er.currency_source_id,
	amsimple.amount_simple_extracted,
	amsimple.currency_extracted,
	er.currency_target_id,
	amsimple.amount_simple_id
FROM
	exchange_rate er 
	LEFT JOIN amount_simple amsimple ON er.amount_simple_target_id = amsimple.amount_simple_id
	LEFT JOIN currency_standardized cs ON er.currency_source_id = cs.currency_standardized_id
ORDER BY
	cs.currency_name,
	amsimple.currency_extracted
```


### Etape 2.7 "Standardisation" des noms des persons et l'extraction de leurs rôles

Voici les tables qui contient les informations sur les personnes:

- participant: les participants de chaque transaction (le point de départ est la transaction, donc les participants peuvent se répéter). L'identifiant "person_id" permet de relier la table "participant" à la table "person".
- person: les personnes (principalement les personnes extraites depuis les comptes, mais on y ajoute également les papes qui sont les émitteurs des comptes). 
- person_role: contient les noms standardisés des roles extraits depuis les comptes.
- person_occupation: permet de relier la table "person" et la table "person_role" (de fait, une personne peut avoir plusieurs roles et le même role peut être attribué à plusieurs personnes, donc la table de lien a été nécaissaire)

Avant commencer le travail sur les personnes et leur roles, on lance le script **postprocessing_2_person_name_and_role.py**.
Ce script permet de:

- standardiser les noms des personnes:
	- a) on prend tous les participants de la table "participant" et on trouve les participants avec les mêmes noms;
	- b) on met ces noms dans la table "person" et le person_id qui est ainsi crée est ajouté à la table "participan".
**Il faudra ensuite, si nécaissaire dans le cadre de programme de recherche, faire un travail de nettoyage de ces données prosopographiques!!!**

- standardiser les noms des rôles:
	- a) on prend tous les roles extraits de la table "participant" et on trouve les roles avec les mêmes noms;
	- b) on met ces noms dans la table "person_role";
	- c) on fait le liens entre ces roles standardisés et la personne par le biais de la table "person_occupation" (chaque line est la paire "person_id, person_role_id").

Ensuite, on fait le nettoyage des roles "standardisés". 
De fait, Après que l'on a regroupé dans le fichier Excel tous les roles extraits depuis la table "person_role" et que l'on a identifié des véritables "noms standardisés" pour tous ces roles extraits, il faudra mettre à jour ces informations dans les tables: "person_occupation" et "person_role". 
Voici les étapes de ce travail:

1) On créer un tableur Excel avec tous les roles extraits depuis les comptes et les roles standardisés auxquels ses roles extraits doivent être associés. Cela permettra de nettoyer et préparer la liste definitive des roles standardisés à retenir. (Pensez à ajouter dans ce tableur Excel les "person_role_id").

2) Mettre à jour la table "person_occupation" selon les roles standardisés retenus.
Après que l'on a regroupé dans le fichier Excel tous les roles extraits depuis la table "person_role" et que l'on a identifié des véritables "noms standardisés" pour tous ces roles extraits, il faudra mettre à jour ces informations dans les tables: "person_occupation" et "person_role". 
Pour cela, à partir de ces "person_role_id" dans tableur Excel avec les roles standardisés à retenir, créer des commandes sql de ce type:
	```
	UPDATE person_occupation
	SET person_role_id = 22
	WHERE person_role_id IN (43, 39, 2, 18, 57);
	```

Explication:
SET person_role_id = 22 - et l'id d'un role standardisé qu'il faut retenir pour un group donné du fichier Excel;
WHERE person_role_id IN (43, 39, 2, 18, 57) - tous les id des roles qui faudra remplacer par l'id du role standardisé donnnée

On peut regrouper tous ces commandes dans un seul fichier sql qui pourra ensuite être executer (par exemple dans le gestionnaire des bases des données).
Voir par exemple le fichier: **1.UPDATE person_occupation.sql**

3) Mettre à jour la table "person_role".

Maintenant, dans la table "person_role" il faut supprimer tous les roles qui n'ont pas été retenu (qui se trouvait alors dans ```WHERE person_role_id IN (43, 39, 2, 18, 57)``` du code sql plus haut).

Pour cela on va utiliser ce code:

```
DELETE FROM person_role
WHERE person_role_id IN (43, 39, 2, 18, 57);

```

Où ```WHERE person_role_id IN (43, 39, 2, 18, 57)```est la liste des person_role_id qu'il faut supprimer.
Voir par exemple le fichier: **2.DELETE person_role.sql**


4) Standardizer manuellement les roles dans la table "person_role".
Maintenant la table person_role ne contient que les roles qui ont été rentenus pour les roles standardisés. Cependant, l'écriture de ces noms est encore n'est pas "propres" car elle reprend les formes (conjugaisons, pluriels, etc.) et les graphies tels qu'ils ont été extrait depuis les comptes. Il faut donc standardiser l'écriture des ces roles.
Pour cela on peut utiliser ce code:

```
UPDATE person_role SET person_role_name_standardized = 'abbas' WHERE person_role_id = 808;
UPDATE person_role SET person_role_name_standardized = 'abreviator' WHERE person_role_id = 566;
UPDATE person_role SET person_role_name_standardized = 'administrator elemosine' WHERE person_role_id = 256;
```
Voir par exemple le fichier: **3.UPDATE person_role (standardizing).sql**



## Etape 4: Post-traitement automatique

L'ensemble des étapes qui suivent (de 4.1 à 4.4.) sont fait par le biais des scripts: 
- postprocessing_3_main.py 
- postprocessing_3_handler_data.py 
- postprocessing_3_handler_exchange_rate.py

Pour lancer l'ensemble des scripts, il suffit de lancer le fichier **postprocessing_3_main.py**

### Etape 4.1 Traitement des montants simples saisie pour les taux de change

Il faut faire le traitement des montants simples saisie lors de la saisie manuele des taux de change.
Lors de ce traitement on fait le travail sur les montants simples pour les déviser en sous-partie, extraite les unités de comptes et extraire les chiffres romains et les convertir en chiffre arabes.


### Etape 4.2 Conversion de tous les montants vers les plus petites unités de comptes

On converti tous les montants simples présents dans la base vers la plus petite unité de compte (on prend "denarius" comme l'unité la plus petite par défaut).


### Etape 4.3 Calcul des taux de change

Le calcul des taux de change nécessite la connaissance des montants convertis vers les plus petites unités de comptes. Pour cette raison, la conversion vers des montants vers les plus petites unités de compte doit être faite au préalable.
De fait, les taux de changes sont toujours exprimé par rapport à l'unité la plus petite de chaque monnaie.

### Etape 4.4 Conversion vers une monnaie commune

Lors de la conversion des montants vers une devise commune, il y a deux étapes:

 - Durant la première étape, tous les montants simples sont convertis. 
 - Durant la deuxième étape, tous les montants simples qui composent un montant composite seront additionnés. À noter toutefois que certains montants simples qui font partie des montants composites doivent être soustraits du montant final (ces montants sont marqués dans la base avec la colonne "opération arithmétique" qui contient la valeur "minus").



## Etape 5: Vérification manuelle après le post-traitement automatique


### Etape 5.1: Vérifier si les montants simples saisies manuellements pour les taux de change ont été correctement traité

Pour les montants "sources" des taux de change:

```
SELECT 
    es.amount_simple_id,
    es.amount_composite_id,
    es.line_id,
    es.amount_simple_extracted,
    es.currency_extracted,
    es.currency_standardized_id,
    es.arithmetic_operator,
    es.amount_simple_remarks,
    es.amount_simple_manuscript_error,
    es.amount_simple_uncertainty,
    es.amount_converted_to_smallest_unit_of_count,
    es.smallest_unit_of_count_uncertainty,
    ass.amount_simple_subpart_id,
    ass.subpart_extracted,
    ass.roman_numeral,
    ass.arabic_numeral,
    ass.amount_simple_subpart_uncertainty,
    ass.unit_of_count_id
FROM 
    exchange_rate er
JOIN 
    amount_simple es ON er.amount_simple_source_id = es.amount_simple_id
LEFT JOIN 
    amount_simple_subpart ass ON es.amount_simple_id = ass.amount_simple_id
```

Pour les montants "cibles" des taux de change:

```
SELECT 
    es.amount_simple_id,
    es.amount_composite_id,
    es.line_id,
    es.amount_simple_extracted,
    es.currency_extracted,
    es.currency_standardized_id,
    es.arithmetic_operator,
    es.amount_simple_remarks,
    es.amount_simple_manuscript_error,
    es.amount_simple_uncertainty,
    es.amount_converted_to_smallest_unit_of_count,
    es.smallest_unit_of_count_uncertainty,
    ass.amount_simple_subpart_id,
    ass.subpart_extracted,
    ass.roman_numeral,
    ass.arabic_numeral,
    ass.amount_simple_subpart_uncertainty,
    ass.unit_of_count_id
FROM 
    exchange_rate er
JOIN 
    amount_simple es ON er.amount_simple_target_id = es.amount_simple_id
LEFT JOIN 
    amount_simple_subpart ass ON es.amount_simple_id = ass.amount_simple_id
```


### Etape 5.2: Vérifier si la conversion vers la plus petite unité de compte a été bien faite pour tous les montants simples déclinables en unités de compte

```
SELECT 
    a.amount_simple_id,
    a.amount_simple_extracted,
    a.amount_converted_to_smallest_unit_of_count
FROM 
    amount_simple_subpart ass
JOIN 
    amount_simple a ON ass.amount_simple_id = a.amount_simple_id
WHERE 
    ass.unit_of_count_id IS NOT NULL
```


### Etape 5.3: Vérifier si les valeurs des taux de changes ont été bien calculé

Voir en entièr la table "exchange_rate".



### Etape 5.4: Vérifier si la conversion vers la monnaie commune (aussi bien pour les montants simples que pour les montants composites) a été bien fait

Voir en entièr la table "amount_converted".




### Etape 5.5: Vérifier si les noms et les rôles des personnes ont été bien "standardisé"


Voir en entièr la table "person".

Après, il faudra également vérifier manuellement les rôles et les "standardiser".

############################################


```
SELECT
	line.document_id,
	line.line_id,
	line.line_number,
	line.folio,
	line.text,
	participant.participant_extracted,
	participant.participant_name_extracted,
	participant.participant_role_extracted,
	participant.additional_participant,
	participant.participant_uncertainty,
	person.person_name_standardized,
	person_function.person_function_name,
	person_type.person_type_name,
	person_role.person_role_name_standardized
FROM
	line
	JOIN participant ON line.line_id = participant.line_id
	JOIN person ON participant.person_id = person.person_id
	JOIN person_function ON participant.person_function_id = person_function.person_function_id
	JOIN person_type ON person.person_type_id = person_type.person_type_id
	JOIN person_occupation ON person.person_id = person_occupation.person_id
	JOIN person_role ON person_occupation.person_role_id = person_role.person_role_id
WHERE
	line.document_id = 1
````



