# tabula-analytics
The University of Warwick's custom administration system [Tabula](https://warwick.ac.uk/services/its/servicessupport/web/tabula/) has a JSON REST API. This is a collection of Python data visualisations using data fetched from this API.

## Disclaimers
This project is neither affiliated with nor endorsed by the Tabula developers or The University of Warwick more generally.  
This project is heavily inspired by [Warwick Wrapped](https://github.com/efbicief/warwick-wrapped).

## Demonstration
![Demonstration](screenshots/demo.gif?raw=True)

## Copyright
Copyright © 2024  Rory Sharp All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

You should have received a copy of the GNU General Public License
along with this program.  If you have not received this, see <http://www.gnu.org/licenses/gpl-3.0.html>.

For a (non-legally binding) summary of the license see https://tldrlegal.com/license/gnu-general-public-license-v3-(gpl-3)

## Installation
1. `python3 -m pip install -r requirements.txt`
2. `cp example_config.yaml config.yaml`
3. `mkdir data`

## Usage
* To (re)load your data from Tabula: Log-in to Tabula in your browser and copy your `__Host-SSO-Tabula-SSC` cookie value into config.yaml, then run `python3 fetch_data.py`
* To run the application: Run `python3 -m gunicorn app:app` and navigate to http://localhost:8000 in your web browser
* To delete your local copy of your data (after all it may well contain information you deem sensitive): `bash purge_data.sh`
