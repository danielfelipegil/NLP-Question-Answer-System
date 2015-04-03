# VERSION 2
# NOTE: Changes in output, dictionary not tuple

# Load in dependancies
import os, sys, re, string, ast, json
from  nltk import *
from corenlp import *
from random import randint
from bs4 import BeautifulSoup
from collections import Counter

debug = False
# non deterministically find important content

# class NLP(object):
#     def __init__(self):
#         self.corenlp = StanfordCoreNLP()
#         return

#     def start(self):
#         return self.corenlp

class Parse(object):
    # textRange 15
    def __init__(self,fileName,dataDir='../sampleData/languages/',textRange=5,ignoreUnicode=True):
        """Parse(fileName,dataDir='../NLP-Question-Answer-System/sampleData/languages/',textRange=5)"""
        self.fileName = fileName
        self.dataDir = dataDir
        self.textRange = textRange+1 # lines of text to search over, +1 for range offset
        self.ignoreUnicode = ignoreUnicode
        print("Reading file..."),
        self.readFile()
        print("OK!")
        print("Tokenizing file..."),
        self.tokenize()
        print("OK!")
        print("Starting StanfordCoreNLP..."),
        self.corenlp = StanfordCoreNLP()
        print("OK!")
        return

    def readFile(self):
        """Load in html file and extract raw text."""
        try:
          html = BeautifulSoup(open(self.dataDir+self.fileName))
          self.raw = html.get_text()
        except:
          raise Exception("Could not read file. Check that the file name and directory are correct. " +
                          "The file extension should be .htm.")
        return 

    def tokenize(self):
        """Tokenize raw text to prepare for parsing."""
        try: 
          misc = self.raw.index("See also")
          self.raw = self.raw[:misc]
        except:
          pass
        self.text = tokenize.sent_tokenize(self.raw)
        self.textLen = len(self.text)
        return

    def getNECounts(self,line):
        """Collect and store counts of named entities within the sentence."""
        try:
            sentence = line[0]['words']
            for token in sentence:
                word = token[0]
                info = token[1]
                if info['NamedEntityTag'] != 'O':
                    self.NEcounts[word] += 1
                    if word not in self.wordNE:
                        self.wordNE[word] = info['NamedEntityTag']
        except:
            raise Exception ("Failed coreNLP parse. \n Text: ", line)
        return

    def getTopicSentence(self,topicNE):
        """Select a sentence with a given named entity."""
        self.topicInd = -1 #get sentence with topic in it
        ind = 0
        while (self.topicInd < 0):
            try:
                tmp = self.parsedText[ind]['sentences'][0]['text']
                if topicNE in tmp:
                   self.topicInd = ind
                else: ind += 1
            except:
                ind += 1
        return

    def treeToList(self,parseTree):
        """Convert parse tree from string to nested array"""
        validChar = string.ascii_letters + string.digits + "() "
        filterChars = (lambda x: ((x in string.punctuation) or
                                  (x not in string.punctuation) or 
                                  (x in "() ")))
        parseTree = ''.join(filter(filterChars, parseTree))
        parseTree = parseTree.replace('(', '[')
        parseTree = parseTree.replace(')', ']')
        parseTree = parseTree.replace('] [', '], [')
        parseTree = parseTree.replace('[]', '')
        parseTree = re.sub(r'(\w+)', r'"\1",', parseTree)
        # punctuation edge cases. may be more not fully tested
        parseTree = parseTree.replace('[. .]', '["."]')
        parseTree = parseTree.replace('[, ,]', '[","]')
        parseTree = parseTree.replace('[: ;]', '[": ;"]')
        parseTree = parseTree.replace('[`` ``]', '["`` ``"]')
        parseTree = parseTree.replace('['' '']', '["'' ''"]')
        try:
            return ast.literal_eval(parseTree)
        except:
            return []

    def selectLine(self):
        (lineFound,attempts) = (False,0)
        uniqueNE = len(list(self.NEcounts))
        topNE = max(uniqueNE // 4, 1)
        mostCommonNE = [k for (k,v) in self.NEcounts.most_common(topNE)]
        topicNE = None
        selectedPhrase = ""
        
        while ((not lineFound) and (attempts < 5)):
            while (topicNE == None):
                try:
                    topicNE = mostCommonNE[randint(0,max(topNE-1,1))]
                except: 
                    print "This sentence has no named entities. Trying new block.."
                    return self.getContent()
            self.getTopicSentence(topicNE)
            try:
                parseTree = self.parsedText[self.topicInd]['sentences'][0]['parsetree']
                rawSentence = self.parsedText[self.topicInd]['sentences'][0]['text']
            except:
                raise Exception ("Invalid parse. Could not decode results.")
            self.parseTree = self.treeToList(parseTree)
            if self.parseTree != []:
                selectedPhrase = self.parseTree[1] # ROOT extracted
                if len(rawSentence.split()) > 6:
                    lineFound = True
            attempts += 1
        if ((attempts > 5) or (selectedPhrase == "")):
            print "Timeout finding line with good content. Trying new block..."
            self.getContent()
        self.resultSent = (selectedPhrase,rawSentence)  
        return 
   
    def getContent(self):
        """Return sentence and corresponding parse tree with important content."""
        # Assumption: python PRNG goodish
        #             there is some worthwhile content every 15 sentences
        startInd = randint(0,self.textLen-self.textRange)
        self.parsedText = []
        self.NEcounts = Counter()
        self.wordNE = dict()
        print ("Parsing lines: "),
        for lineInd in xrange(startInd,startInd+self.textRange):
            print lineInd,
            line = self.text[lineInd]
            if isinstance(line, unicode):
                try: 
                    parsedLine = self.corenlp.parse(line)
                    lineToLoad = unicode(parsedLine, 'utf-8')
                    res = json.loads(lineToLoad)
                    self.parsedText.append(res)
                    self.getNECounts(res['sentences'])
                except: 
                    # return parsedLine, lineToLoad, line
                    # raise Exception ("Json encoding error.")
                    pass # is not real sentence
            else: raise Exception ("Invalid encoding for text file.")
        print "Block Complete."
        self.selectLine()
        self.results = dict()
        self.results["parsedSentence"] = self.resultSent[0]
        self.results["rawSentence"] = self.resultSent[1]
        self.results["wordNE"] = self.wordNE
        return self.results
