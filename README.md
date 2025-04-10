# GrandStellarisArchivalProject
A Stellaris Companion Tool. Imagine if you could make a research agreement the the Curators *but they could also break the fourth wall to give game advice* ~~Totally not lowkey rebuilding the wiki from scratch~~

Will be viewable and accessable at stellaris.HooverTesla.com


***********************************************************
************************ DEV NOTES ************************
***********************************************************

Just wanted to make sure you read the README before breaking shit and whining about it.
## **Rosetta -> Scraper/Grabber/Extractor**
  -> Translates PDX nonsense to a nice clean ~~CSV~~ JSON file-Hence Rosetta stone reference
  -> Also beware that PDX puts @foo = 3 shit at the top of files then calls the var later so this will just apply the variable then export the whole number instead of @ foo for the value.
## **Forge -> Processor**
  -> Processes the Raw input(ores) into workable tools, like variables and modifiers
  -> Will probably[^1] have each major category as it's own file for y'all's sakes when I inevitably do my ASD thing and find a different special interest for an indeterminate amount of time.
## **Unknown -> Parser**
  -> the one click shop for running the damn thing, probably[^1] just calling the other files in the folder.


## ** Glossary **
 - _foo = metadata of some sort, line numbers, comments from the OG stellaris file, others
 - "FROM" is used in things like 00_diplo_greetings to reference an empire in game, NOT do the thingy that python  wants to do with dicts so it gets handled a little funny, "_EXTERNAL_FROM_BLOCK"
 - ROOT

[^1]: - What? It's 4/5/25 and I haven't built the damn thing yet. So "probably" is me trying to premetively convince me to do good coding habits and also like, do the documentation knowing that I suck at remembering to come back and update things like this. Also if I write down the names of the files that work in my head then I will rememeber the names that make sense in my head and not switch through variants of translators/extractor from books like it's a random number generator. rn everything is shoved into one file called parse_anom_LIVE because I gave up on renaming the stupid thing every iterative update. So... probably is a good thing! Unless I don't stick to it, in which case my name is Hoover and you can mutter my name under your breath in a British Accent and pretend to be a pretentious blond jackass.

***********************************************************
***********************************************************

***********************************************************
***********************************************************
## Rosetta

### Required info:
Config input/output paths
Go line by line checking characters
    REGEX?
 If # -> Break
Grab val of "@variable = int" values and store them
Grab ID from:
  0:ID = {
Grab desc value
  1:  desc = "string"
Grab picture reference/var/thingyIDKTheNameOf
  1:  picture = val
Grab level val OR @var and replace with value
  1:  level = 1
        OR
  1:  level = @var
Grab anything with "= {" and grab ID, and dict object.
  1:  spawn_chance = {
        modifier = {
          add = int
          is_asteroid = bool
          num_minerals (<, >, ==, !=) int
        }
  }
Grab max_once bool
  1:  max_once = yes/no





Throw this away ask ChatGPT to give you code that translates PDX to JSON.
Then ask it to add the @var shit
