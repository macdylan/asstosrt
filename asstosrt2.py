#! /usr/bin/env python
#coding: utf-8

#    <asstostr2 - Convert ASS to SRT >
#    Copyright (C) <2011>  <XiErCh>

#    Ver 0.4.4
#    http://xierch.tk/archives/py-ass2srt/

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, os
import re #用于识别 {特效代码}

sys.path.append('atslib.zip')
chkcode, canlangconv = (True, True)
try:
    import chardet #用于识别文件编码
except:
    print('** WARN: Please install "chardet", spot coding of ass files.\nOtherwise please the encoding is UTF-8.')
    chkcode = False
try:
    from langconv import langconv #繁简体转换
except:
    print("** Simplified-Traditional Translator is't found.")
    canlangconv = False

class Ass2Srt():
    def __init__(self, assurl = None, srturl = None):
        self.assurl = assurl
        self.srturl = srturl


    def tosrt(self,
              assurl = None,
              srturl = None,
              encode = 'utf-16', #输出srt文件的编码
              resort = True, #True-重新排序
              deleffect = True, #True-删除所有带进入特的字幕
              deline = False, #Ture-仅保留第一行字幕
              translate = None): #'zh-hans'-转换为简体; 'zh-hant'-转换为繁体
        '''Convert ASS to SRT

        assurl: ASS file address
        srturl: Output file address
        resort: Re-sort SRT by time again
        deline: Only save the first line (When there is \\N)
        deleffect: Delete lines that have transition effects
        translate: zh-hans or zh-hant
        '''

        if assurl == None:
            assurl = self.assurl
        if srturl == None:
            if self.srturl == None:
                srturl = assurl[:-4] + '.srt'
            else:
                srturl = self.srturl

        ass = open(assurl, 'rb')
        srt = open(srturl, 'wb')
        assbyte = ass.read()

        #解码：
        if chkcode:
            inencoding = chardet.detect(assbyte)['encoding']
        else:
            inencoding = 'UTF-8' #默认按UTF-8处理
        asstxt = assbyte.decode(inencoding, 'ignore')

        #繁简体转换：
        if canlangconv and translate != None:
            langcer = langconv.Converter(translate)

        asslines = asstxt.splitlines()
        sublst = [] #字幕列表按此格式保存在此处：[[Start, End, Text], ...]
        nostart, noend, notext, noeffect =(-1, -1, -1, -1)

        inEvents = False #是否已经进入[Events]中
        for line in asslines:

            if line == '':
                continue #跳过空行

            if inEvents:
                if line[0] == '[': #检查[Events]是否结束
                    break #结束
            else:
                if line == '[Events]': #检查是否进入[Events]
                    inEvents = True
                continue

            if line[:9] == 'Dialogue:': ##### 处理字幕行：
                if nostart == -1 or noend == -1 or notext == -1: #检查是否已获取字幕行格式Format
                    raise IOError("Format isn't found, or it is after Dialogue.")

                #若需要，忽略带过渡特效的字幕（如顶部滚动版权警告）
                if deleffect and noeffect != -1:
                    if self.__findpice(line, noeffect) != '':
                        continue                    

                #读取 Start, End Text:
                lstart = self.__findpice(line, nostart) #Start
                lend = self.__findpice(line, noend) #End
                ltext = self.__findpice(line, notext, True) #Text

                #忽略 Start == End：
                if lstart == lend:
                    continue

                #删除{}内特效代码：
                re_code = re.compile(r'{.*?}')
                codelst = re_code.findall(ltext)
                for code in codelst:
                    ltext = ltext.replace(code, '')

                #处理强制换行 \N：
                fstart = ltext.find(r'\N')
                if fstart != -1:
                    if deline: #若需要，删除\N后内容（仅保留首行）：
                        ltext = ltext[:fstart] #一些字幕将英文放在第二行显示 -_-||
                    else:
                        ltext = ltext.replace(r'\N', ' ')

                #处理繁简转换：
                if translate != None and canlangconv:
                    ltext = langcer.convert(ltext)

                #加入到列表：
                #print [lstart, lend, ltext]
                sublst.append([lstart, lend, ltext])

            elif line[:7] == 'Format:': ##### 取得字幕行格式(nostart, noend, noeffect, notext)：
                line = line.lower()
                #Text:
                if line[-4:] != 'text': #暂不支持不以Text结尾的格式，因为不知道怎么处理字幕中含逗号
                    raise IOError('Dialogue ends without Text.')
                notext = line.count(',')
                #Start:
                fstart = line.find('start')
                if fstart == -1:
                    raise IOError("Start isn't found on Format.")
                nostart = line.count(',', 0, fstart)
                #End:
                fstart = line.find('end')
                if fstart == -1:
                    raise IOError("End isn't found on Format.")
                noend = line.count(',', 0, fstart)
                #Effect:
                if deleffect:
                    fstart = line.find('effect')
                    if fstart != -1:
                        noeffect = line.count(',', 0, fstart)
                #print (nostart, noend, notext, noeffect)

        #检查结果：
        if len(sublst) == 0 :
            if chkcode == False:
                print('Please install "chardet" (http://chardet.feedparser.org/download/) to solve the file coding porblem.')
            else:
                print('** Error: Subtitle is not found in the file.\nPlease the file is ass-file.')
            raise IOError()

        #如需要，重新对字幕排序：
        if resort and len(sublst) > 1: #效率极低的冒泡排序 -_-||
            for end in range(len(sublst) - 1, 0, -1):
                sorted = False
                for i in range(0, end):
                    if(self.__isfornt(sublst[i][0], sublst[i + 1][0]) == False): #按 Begin 排序 
                        temp = sublst[i] #顺序不对，替换之
                        sublst[i] = sublst[i + 1]
                        sublst[i + 1] = temp
                        sorted = True
                if sorted == False:
                    break #一次循环无对调，说明已经正确排序

        #调整为SRT格式并写出：
        i = 0
        srtout = ''
        for x in sublst:
            i += 1
            #print(x[0] + ' ' + x[1] + ' ' + str(x[2]))
            srtout += '%s\r\n%s --> %s\r\n%s\r\n\r\n' % (str(i), x[0].replace('.', ','), x[1].replace('.', ','), x[2])
        srt.write(srtout.encode(encode, 'ignore'))

        ass.close()
        srt.close()

    def __findpice(self, line, no, text=False):
        fstart = 0
        for i in range(no):
            fstart = line.find(',', fstart) + 1
        fend = line.find(',', fstart)
        if fend == -1 or text:
            fend = len(line)
        return line[fstart:fend]


    def __isfornt(self, fornt, back):
        fornt_int = float(fornt.replace(':', ''))
        back_int = float(back.replace(':', ''))
        #print(fornt + ' <= ' + back)
        #print(fornt_int <= back_int)
        return fornt_int <= back_int

if __name__ == '__main__':
    #设置编码：
    if sys.getdefaultencoding() != 'utf-8':
        reload(sys)
        sys.setdefaultencoding('utf-8')

    #检测拖拽入的文件：
    filelst = sys.argv
    del filelst[0]
    if len(filelst) == 0:
        print('Auto scanning ass-files...')
        #扫描运行目录下的文件：
        allfile = os.listdir(os.getcwd())
        for file in allfile:
            if file.endswith('.ass') or file.endswith('.ssa'):
                filelst.append(file)
    if len(filelst) == 0:
        print('No found any ass-file.')
        raw_input()
        sys.exit()

    print('%s files will be transformed.' % str(len(filelst)))

    atos = Ass2Srt()
    i, fail = (0, 0)
    for file in filelst:
        i += 1
        print('(%s/%s) is transforming ... ' % (str(i), str(len(filelst))))
        try:
            atos.tosrt(assurl = file)
            print('done')
        except IOError, e:
            fail += 1
            print('** Fail: ' + e.message)
            continue
        except:
            fail += 1
            continue

    if fail == 0:
        print('Success! All done.')
    else:
        print('%s done, %s failed.' % (str(i-fail), str(fail)))
        raw_input()