Get-a-GUID
=================

Derek Merck <derek_merck@brown.edu>  
Brown University and Rhode Island Hospital  
Winter 2018


## Overview

Python library and Flask REST api to generate 1-way hashes for study ids, pseudonyms, and approximate-birth-date for globally consistent identifiers in study anonymization.

A reference web implementation of the most recent master branch is available at <http://get-a-guid.xn--zm-mka.biz.biz>.


## Dependencies

- Python 2.7
- [Flask](http://flask.pocoo.org)
- markdown


## Usage

To use it as a Python library:

````python
>>> import GUIDMint
>>> mint = GUIDMint.PseudoMint()
>>> mint.mint_guid( "MERCK^DEREK^L" )
u'AYJOAUVBBT54F6TP'
````

To create a local server instance:

```bash
$ python get_a_guid.py &  
  * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)  
$ curl "localhost:5000/guid/pseudonym/pseudo_id?value=MERCK^DEREK^L"
{"dob": "1968-07-25", "gender": "U", "guid": "AYJOAUVBBT54F6TP", "name": "ANDRONIS^YEVETTE^J"}
```

## Algorithm

Multiple algorithms ('mints') are available.  The `md5` mint simply hashes the `name` parameter to create a name and id, and generates an approximate-date-of-birth.

```bash
$ curl "localhost:5000/guid/md5/pseudo_id?value=MERCK^DEREK^L"
{ "dob": "1966-03-16", "gender": "U", "guid": "392ec5209964bfad", "name": "392ec5209964bfad"}
```

Other mint classes can be created by overriding basic functionality and then easily plugged into the architecture.

### PseudMint Global Unique Identifier (GUID)

This must generate a unique and reproducibly generated tag against any consistent set object-specific variables.

Generation method:

1. A `value` parameter is passed in; depending on the available data, this may be a patient name, an MRN, or a subject ID, or any unique combination of those elements along with gender and dob
2. The [sha256](http://en.wikipedia.org/wiki/Secure_Hash_Algorithm) hash of the value is computed and the result is encoded into [base32](http://en.wikipedia.org/wiki/Base32)
3. If the first three characters are not alphabetic, the value is rehashed until it is (for pseudonym generation)
4. By default only the 64 bit prefix is used and any padding symbols are stripped.

  
### Pseudonyms

It is often useful to replace the subject name with something more natural than a GUID.  
Any string beginning with at least 3 (capitalized) alphabetic characters can be used to reproducibly generate a ["John Doe"](http://en.wikipedia.org/wiki/John_Doe) style placeholder name in DICOM patient name format (`last^first^middle`).  This is very useful for alphabetizing subject name lists similarly to their ID while still allowing for anonymized data sets to be referenced according to memorable names.

Generation method:

1. A `guid` parameter is requried and `gender` (M,F,U) is optional (defaults to U)
2. Using the `guid` as a random seed, a gender-appropriate first name and gender-neutral family name is selected from a uniform distribution taken from the US census
3. The result is returned in DICOM patient name format.

[pname_fmt]:(http://support.dcmtk.org/docs/classDcmPersonName.html#f8ee9288b91b6842e4417185d548cda9)

```bash
$ curl "localhost:5000/guid/pseudonym/pseudo_id?value=MERCK^DEREK^L&gender=M"
{"dob": "1956-02-03", "gender": "M", "guid": "MLSUJGK22EKMCMBX", "name": "MEMS^LIONEL^S"}
$ curl "localhost:5000/guid/pseudonym/pseudo_id?value=MERCK^DEREK^L&gender=M"
{"dob": "1961-03-20", "gender": "F", "guid": "IRF4WKGJGW36GQKJ", "name": "IACOPINO^RANDA^F"}
```

_Note that each (value, gender, dob) tuple will result in a unique ID!_

The default name map can be easily replaced to match your fancy (Shakespearean names, astronauts, children book authors).  And with slight modification, a DICOM patient name with up to 5 elements could be generated (i.e., in `last^first^middle^prefix^suffix` format).


### Approximate Date-of-Birth

As with pseudonyms, it can be useful to maintain a valid date-of-birth (dob) in de-identified metadata.  Using a GUID as a seed, any dob can be mapped to a random nearby date for a nearly-age-preserving anonymization strategy.  This is useful for keeping an approximate patient age available in a data browser.


Generation method:

1. A `dob` parameter in `%Y-%m-%d` format and `guid` parameter are required
2. Using the `guid` as a random seed, a random integer between -165 and +165 is selected
3. The original `dob` + the random delta in days is returned


### Creating a Pseudo-Identity

A pseudo-id is merely an alias for generating a GUID, pseudonym, and pseudo-dob from a subject name/id/mrn, gender, and dob.
 
Generation method:

1. An initial `value` is parameter is required, either `dob` in `%Y-%m-%d` format or `age` parameter is optional (defaults to a uniform random value between 19 and 65), and a `gender` parameter (M,F,U) is optional (defaults to U)
2. If `age` is given, it is converted to a `dob` estimate using `dob=now()-365.25*age`
3. A `guid` is computed using the concatenation of `value|dob|gender` as a seed (thus, the `guid` is _not_ the same as the `guid` hash of only the initial value)
4. A pseudonym and pseudodob are computed as above
5. The `guid` and new `name` and `dob` are returned


## Implementing as a Public Service

To create a [Heroku](http://www.heroku.com) server instance:

```bash
$ heroku create
$ git push heroku master
$ heroku ps:scale web=1
$ curl "http://get-a-guid.herokuapp.com/pseudonym/pseudo_id?name=MERCK^DEREK^L"
{"dob": "1968-07-25", "gender": "U", "guid": "AYJOAUVBBT54F6TP", "name": "ANDRONIS^YEVETTE^J"} 
```

Single dyno Heroku instances are free to run, but can take a minute to startup after they fall asleep.

To create a [Dokku](http://dokku.viewdocs.io/dokku/) server instance:

```bash
$ git clone https://github.com/derekmerck/DIANA
$ cd DIANA
$ git add remote dokku dokku@xn--zm-mka.biz:get-a-guid
$ git subtree push --prefix GUIDMint dokku master
$ curl "http://get-a-guid.xn--zm-mka.biz/pseudonym/pseudo_id?name=MERCK^DEREK^L"
{"dob": "1968-07-25", "gender": "U", "guid": "AYJOAUVBBT54F6TP", "name": "ANDRONIS^YEVETTE^J"} 
```


## Acknowledgements

- Inspired in part by the [NDAR](https://ndar.nih.gov/ndarpublicweb/tools.html) and [FITBIR](https://fitbir.nih.gov) GUID schema.
- Thanks for the [Heroku](http://www.heroku.com) Flask tutorials at <http://virantha.com/2013/11/14/starting-a-simple-flask-app-with-heroku/> and <http://stackoverflow.com/questions/17260338/deploying-flask-with-heroku> and <http://www.moreiscode.com/dokku-error/>
- GitHub markdown css from <https://github.com/sindresorhus/github-markdown-css>
- Placeholder names inspired by the [Docker names generator](https://github.com/docker/docker/blob/master/pkg/namesgenerator/names-generator.go)


## License

[MIT](http://opensource.org/licenses/mit-license.html)

