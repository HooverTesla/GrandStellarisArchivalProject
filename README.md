# GrandStellarisArchivalProject
A Stellaris Companion Tool. Imagine if you could make a research agreement the the Curators *but they could also break the fourth wall to give game advice* ~~Totally not lowkey rebuilding the wiki from scratch~~ 

Will be viewable and accessable at stellaris.HooverTesla.com


***********************************************************
************************ DEV NOTES ************************
***********************************************************

Just wanted to make sure you read the README before breaking shit and whining about it. 
## **Rosetta -> Scraper/Grabber/Extractor**
  -> Translates PDX nonsense to a nice clean CSV file-Hence Rosetta stone reference
  -> Also beware that PDX puts @foo = 3 shit at the top of files then calls the var later so this will just apply the variable then export the whole number instead of @ foo for the value.  
## **Forge -> Processor**
  -> Processes the Raw input(ores) into workable tools, like variables and modifiers
  -> Will probably[^1] have each major category as it's own file for y'all's sakes when I inevitably do my ASD thing and find a different special interest for an indeterminate amount of time. 
## **Unknown -> Parser**
  -> the one click shop for running the damn thing, probably[^1] just calling the other files in the folder.



[^1]: - What? It's 4/5/25 and I haven't built the damn thing yet. So "probably" is me trying to premetively convince me to do good coding habits and also like, do the documentation knowing that I suck at remembering to come back and update things like this. Also if I write down the names of the files that work in my head then I will rememeber the names that make sense in my head and not switch through variants of translators/extractor from books like it's a random number generator. rn everything is shoved into one file called parse_anom_LIVE because I gave up on renaming the stupid thing every iterative update. So... probably is a good thing! Unless I don't stick to it, in which case my name is Hoover and you can mutter my name under your breath in a British Accent and pretend to be a pretentious blond jackass. 

***********************************************************
***********************************************************
