# GUIDMint

[Derek Merck](email:derek_merck@brown.edu)  

<https://github.com/derekmerck/diana/apps/guid-mint>


## Overview

Python library and Flask app to generate 1-way hashes for globally consistent identifiers in study anonymization.

A reference web implementation of the most recent master branch is available at <http://get-a-guid.herokuapp.com>.

It is intended to be used as an adjunct with an automatic anonymization framework like [XNAT's](http://www.xnat.org) [DicomEdit](http://nrg.wustl.edu/software/dicomedit/).  A reference anonymization script using `get-a-guid` is available here: <https://gist.github.com/derekmerck/5d4f40a7b952525a09c4>.


## Dependencies

- Python 2.7
- [Flask](http://flask.pocoo.org)
- markdown


## Usage

To use it as a Python library:

````python
>>> from GUIDMint import GUIDMint
>>> mint = GUIDMint()
>>> mint.mint_guid( "MERCK^DEREK^L" )
BEW6DDOU
````

To create a local server instance:

```bash
$ python Get_a_GUID.py &  
  * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)  
$ curl -4 "localhost:5000/guid?value=MERCK^DEREK^L"
BEW6DDOU  
```

To create a public [Heroku](http://www.heroku.com) server instance:

```bash
$ heroku create
$ git push heroku master
$ heroku ps:scale web=1
$ curl "http://get-a-guid.herokuapp.com/guid?value=MERCK^DEREK^L"
BEW6DDOU 
```

Single dyno Heroku instances are free to run, but can take a minute to startup after they fall asleep.


### Global Unique Identifier (GUID)

This is the basic functionality, which is simply intended to be a unique and reproducibly generated tag against any consistent set object-specific variables.

Generation method:

1. A `value` parameter is passed in; depending on the available data, this may be a patient name, an MRN, or a subject ID, or any unique combination of those elements along with gender and dob
2. The [sha256](http://en.wikipedia.org/wiki/Secure_Hash_Algorithm) hash of the value is computed and the result is encoded into [base32](http://en.wikipedia.org/wiki/Base32)
3. If the first three characters are not alphabetic, the value is rehashed until it is (for pseudonym generation)
4. By default only the 64 bit prefix is used and any padding symbols are stripped.

Example: <http://get-a-guid.herokuapp.com/guid?/guid?value=MERCK^DEREK^L">
  `{'guid': 'BEW6DDOU'}`
  
  
### Pseudonyms

It is often useful to replace the subject name with something more natural than a GUID.  
Any string beginning with at least 3 (capitalized) alphabetic characters can be used to reproducibly generate a ["John Doe"](http://en.wikipedia.org/wiki/John_Doe) style placeholder name in [DICOM patient name format][pname_fmt].  This is very useful for alphabetizing subject name lists according to generic ID and for referencing anonymized data sets according to memorable names.

Generation method:

1. A `guid` parameter is requried and `gender` (M,F,U) is optional (defaults to U)
2. Using the `guid` as a random seed, a gender-appropriate first name and gender-neutral family name is selected from a uniform distribution taken from the US census
3. The result is returned in [DICOM patient name format][pname_fmt].

Example: <http://get-a-guid.herokuapp.com/guid?/guid?value=MERCK^DEREK^L">
  `{'guid': 'BEW6DDOU'}`

[pname_fmt]:(http://support.dcmtk.org/docs/classDcmPersonName.html#f8ee9288b91b6842e4417185d548cda9)

The default name map can be easily replaced to match your fancy (Shakespearean names, astronauts, children book authors).  And with slight modification, a DICOM patient name with up to 5 elements could be generated (last^first^middle^prefix^suffix).

<http://get-a-guid.herokuapp.com/name?value=AUUNVBGA5JKUE>  
`Andronicus^Ulysses^U^Nurse^of Verona`


### Pseudo Date-of-Birth

As with pseudonyms, it can be useful to maintain a valid date-of-birth (dob) in de-identified metadata.  Using a GUID as a seed, any dob can be mapped to a random nearby date for a nearly-age-preserving anonymization strategy.  This is useful for keeping an approximate patient age available in a data browser.


Generation method:

1. A `dob` parameter in `%Y-%m-%d` format and `guid` parameter are required
2. Using the `guid` as a random seed, a random integer between -165 and +165 is selected
3. The original `dob` + the random delta in days is returned

<http://get-a-gid.herokuapp.com/pdob?dob=19710101&guid=AUUNVBGA5JKUE>  
`19710830`


### Creating a Pseudo-Identity

A pseudo-id is merely an alias for generating a GUID, pseudonym, and pseudo-dob from a subject name/id/mrn, gender, and dob.
 
Generation method:

1. An initial `value` is parameter is required, either `dob` in `%Y-%m-%d` format or `age` parameter is required, a `gender` parameter (M,F,U) is optional (defaults to U)
2. If `age` is given, it is converted to a `dob` estimate using `dob=now()-365.25*age`
3. A `guid` is computed using the concatenation of `value|dob|gender` as a seed (thus, the `guid` is _not_ the same as the `guid` hash of only the initial value)
4. A pseudonym and pseudodob is computed as above
5. The `guid` and new `name` and `dob` are returned

<http://get-a-guid.herokuapp.com/pseudo_identity?value=MERCK^DEREK^L&dob=19710101&gender=M>  
`AUUNVBGA5JKUE`


## Acknowledgements

- Inspired in part by the [NDAR](https://ndar.nih.gov/ndarpublicweb/tools.html) and [FITBIR](https://fitbir.nih.gov) GUID schema.
- Thanks for the [Heroku](http://www.heroku.com) Flask tutorials at <http://virantha.com/2013/11/14/starting-a-simple-flask-app-with-heroku/> and <http://stackoverflow.com/questions/17260338/deploying-flask-with-heroku>
- GitHub markdown css from <https://github.com/sindresorhus/github-markdown-css>
- Placeholder names inspired by the [Docker names generator](https://github.com/docker/docker/blob/master/pkg/namesgenerator/names-generator.go)


## License

[MIT](http://opensource.org/licenses/mit-license.html)


## Future Work

- Use a database to link an already generated identifier hash to other source values.  For example, an already generated GUID could be linked to a study ID, so relevant GUID queries against that ID would also return the original GUID hash.  The main drawback to this is that it would require a single central server and persistent memory.

- Check for collisions in a given namespace and, if needed, create a new hash and link as above.  (Possibly using an alternate hash algorithm when collisions are detected.)

- Translate requests directly to the NDAR GUID generator to facilitate data enrollment in FITBIR.