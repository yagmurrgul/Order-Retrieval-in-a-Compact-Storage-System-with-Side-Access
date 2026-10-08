using System;
using System.Diagnostics;
using System.Collections.Generic;
using System.Text;
using System.Collections;

namespace Aulokomp
{
    class cDP
    {      
        public double timeLimit;
        public long stateCounter;
        public Hashtable[] lookUp;
        public Stack<cNode>[] nodeList;
        public cNode currentNode;


        public Stopwatch watch;

        public cDP(double limit)
        {
            //
            // TODO: Fügen Sie hier die Konstruktorlogik hinzu
            //
            cNode tempNode;

            lookUp = new Hashtable[cData.num_Boxes + 1];
            for (int i = 0; i <= cData.num_Boxes;i++)
            {
                lookUp[i] = new Hashtable();

            }

            nodeList = new Stack<cNode>[cData.num_Boxes];


            for (int i = 0; i < cData.num_Boxes; i++)
            {
                nodeList[i] = new Stack<cNode>();
            }

            tempNode = new cNode(new bool[cData.num_Boxes]);
            lookUp[0].Add("", tempNode);
            timeLimit = limit;
            watch = new Stopwatch();
            stateCounter = 1;
        }


        public bool solveDP()
        {
            
            int newBox;
            bool dom;

            cNode tempNode, newNode;

            
            bool[] tempAssigned = new bool[cData.num_Boxes];
            String capString;
            IDictionaryEnumerator myEnum;
            
            cSolution.initMe();

            watch.Start();
            for (int i = 0; i < cData.num_Boxes; i++)
            {
                
                myEnum = lookUp[i].GetEnumerator();
                while (myEnum.MoveNext())
                {

                    currentNode = (cNode)myEnum.Value;               

                   cSolution.resetMe(currentNode);
                  
                    if (!currentNode.dominated) {
                        stateCounter++;

                        newBox = cSolution.getLeftTopDominance();
                        if (newBox != -1 && cSolution.getAccessibility(newBox))
                        {
                            tempAssigned = new bool[cData.num_Boxes];

                            Array.Copy(currentNode.assigned, tempAssigned, cData.num_Boxes);
                            tempAssigned[newBox] = true;

                            tempNode = new cNode(tempAssigned, currentNode);
                            tempNode.objVal = currentNode.objVal + cSolution.getObjective(newBox, -1);

                            nodeList[0].Push(tempNode);

                            //Start pinning cycles if not the last box
                            if (i < cData.num_Boxes - 1)
                            {
                                dom = false;
                                // Pinning Cycle in the same tier
                                for (int l = 1; l < cSolution.boxByTier[cSolution.maxHeight].Count; l++)
                                {
                                    if (cSolution.getFeasibility(cSolution.boxByTier[cSolution.maxHeight][l]) && cSolution.getAccessibility(cSolution.boxByTier[cSolution.maxHeight][l]))
                                    {
                                        pinningCycle(cSolution.maxHeight, l, 0, cData.boxColumn[newBox], cSolution.maxHeight, cData.boxColumn[newBox], cData.boxColumn[newBox], true, dom);
                                        if (!dom && cSolution.checkPinningDominance(cData.boxColumn[newBox], cSolution.boxByTier[cSolution.maxHeight][l]))
                                        {
                                            dom = true;
                                        }
                                    }

                                }
                                // picking one tier below
                                if ((cSolution.maxHeight > 0 && cSolution.boxByTier[cSolution.maxHeight - 1].Count > 0 && cData.boxColumn[cSolution.boxByTier[cSolution.maxHeight - 1][0]] == 0) && cSolution.getFeasibility(cSolution.boxByTier[cSolution.maxHeight - 1][0]))
                                {

                                    pinningCycle(cSolution.maxHeight - 1, 0, 0, cData.boxColumn[newBox], cSolution.maxHeight, cData.boxColumn[newBox], cData.boxColumn[newBox], false, false);
                                    if (!tempNode.dominated && cSolution.checkPinningDominance(cData.boxColumn[newBox], cSolution.boxByTier[cSolution.maxHeight - 1][0]))
                                    {
                                        tempNode.dominated = true;
                                    }
                                }

                                

                            }

                        }
                        else
                        {
                            for (int j = cSolution.maxHeight; j >= 0; j--)
                            {
                                for (int k = 0; k < cSolution.boxByTier[j].Count; k++)
                                {
                                    
                                    newBox = cSolution.boxByTier[j][k];
                                    if (!currentNode.assigned[newBox] && cSolution.getAccessibility(newBox) && cSolution.getFeasibility(newBox))
                                    {

                                       
                                        tempAssigned = new bool[cData.num_Boxes];

                                        Array.Copy(currentNode.assigned, tempAssigned, cData.num_Boxes);
                                        tempAssigned[newBox] = true;

                                        tempNode = new cNode(tempAssigned, currentNode);
                                        tempNode.objVal = currentNode.objVal + cSolution.getObjective(newBox, -1);

                                        if (cSolution.checkOnTopDominance(newBox)) {
                                            // if there is an unassigned box on top of this one it doesn't need to be branched
                                            
                                            tempNode.dominated = true;
                                        }

                                        nodeList[0].Push(tempNode);


                                        //Start pinning cycles if not the last box
                                        if (i < cData.num_Boxes - 1)
                                        {
                                            // Pinning Cycle in the same tier
                                            dom = false;
                                            for (int l = k + 1; l < cSolution.boxByTier[j].Count; l++)
                                            {
                                                if (cSolution.getAccessibility(cSolution.boxByTier[j][l]) && cSolution.getFeasibility(cSolution.boxByTier[j][l]))
                                                {
                                                    pinningCycle(j, l, 0, cData.boxColumn[newBox], j, cData.boxColumn[newBox], cData.boxColumn[newBox], true, dom);
                                                    if (!dom && cSolution.checkPinningDominance(cData.boxColumn[newBox], cSolution.boxByTier[j][l]))
                                                    {
                                                        dom = true;
                                                    }
                                                }

                                            }

                                            if ((j > 0 && cSolution.boxByTier[j - 1].Count > 0 && cData.boxColumn[cSolution.boxByTier[j - 1][0]] == 0) && cSolution.getFeasibility(cSolution.boxByTier[j - 1][0]))
                                            {

                                                pinningCycle(j - 1, 0, 0, cData.boxColumn[newBox], j, cData.boxColumn[newBox], cData.boxColumn[newBox], false, false);
                                                if (!tempNode.dominated && cSolution.checkPinningDominance(cData.boxColumn[newBox], cData.boxColumn[cSolution.boxByTier[j - 1][0]]))
                                                {
                                                    tempNode.dominated = true;
                                                }
                                            }

                                            

                                        }

                                    }
                                }
                            }
                        }
                    

                        // Add Nodes to hashtable
                        for (int j = 0; j < cData.num_Boxes; j++)
                        {
                            while (nodeList[j].Count > 0)
                            {
                                newNode = nodeList[j].Pop();
                                    capString = "";
                                    for (int k = 0; k < cData.num_Boxes; k++)
                                    {
                                        capString += Convert.ToString(newNode.assigned[k]) + "-";
                                    }
                                    tempNode = (cNode)lookUp[i + j + 1][capString];
                                    if (tempNode == null)
                                    {
                                       
                                        lookUp[i + j + 1].Add(capString, newNode);
                                    }
                                    else
                                    {
                                        if (newNode.objVal < tempNode.objVal)
                                        {
                                             lookUp[i + j + 1][capString] = newNode;
                                        }
                                       
                                    }
                            }
                        }

                    }

                    if (watch.Elapsed.TotalSeconds > timeLimit)
                    {
                        watch.Stop();
                        return false;
                    }
                }
                
            }
               
            watch.Stop();

            return true;
        }

        private void pinningCycle(int tier, int count, int nrAssigned, int pinnedColumn, int pinnedTier, int pickedColumn, bool obj, bool dominated) {
            int newBox, newColumn;
            cNode actNode, tempNode;
            bool[] tempAssigned;
            bool dom = dominated;

            actNode = nodeList[nrAssigned].Peek();            
            newBox = cSolution.boxByTier[tier][count];
            newColumn = cData.boxColumn[newBox];

            tempAssigned = new bool[cData.num_Boxes];

            Array.Copy(actNode.assigned, tempAssigned, cData.num_Boxes);
            tempAssigned[newBox] = true;

            tempNode = new cNode(tempAssigned, currentNode);

            tempNode.dominated = dominated;
            if (obj) {
                tempNode.objVal = actNode.objVal + cSolution.getObjective(newBox,pinnedColumn);
            } else {
                tempNode.objVal = actNode.objVal;
            }
            nodeList[nrAssigned + 1].Push(tempNode);

            // all boxes in the same tier are fair game if we are in this tier or if we "tunneled" to this tier
                if (tier == pinnedTier || pinnedColumn == newColumn) {
                for (int i = count + 1; i < cSolution.boxByTier[tier].Count; i++)
                {
                    
                    if (cSolution.getAccessibility(cSolution.boxByTier[tier][i]) && cSolution.getFeasibility(cSolution.boxByTier[tier][i]))
                    {
                        pinningCycle(tier, i, nrAssigned + 1, newColumn, tier, newColumn, true, dom);
                        // if the box just assigned fulfills dominance criteria, all cycles not containing the box are dominated
                        if (!dom && cSolution.checkPinningDominance(newColumn, cSolution.boxByTier[tier][i])) {
                         dom = true;
                      }
                    }
                }
               
            } else if (count < cSolution.boxByTier[tier].Count - 1) {
                // we have sunk down a tier, only consider adjacent neighbors neighbors until the column that has been picked totally
                
                if (cData.boxColumn[cSolution.boxByTier[tier][count + 1]] == newColumn + 1 && cData.boxColumn[cSolution.boxByTier[tier][count + 1]] <= pickedColumn && cSolution.getFeasibility(cSolution.boxByTier[tier][count + 1])) {
                        pinningCycle(tier, count+1, nrAssigned + 1, pinnedColumn, pinnedTier, pickedColumn,false, dominated);
                    if (!tempNode.dominated && cSolution.checkPinningDominance(newColumn, cSolution.boxByTier[tier][count +1]))
                    {
                        tempNode.dominated = true;
                    }
                }
            }
            // pinning cycle can also be continued a tier below in the first column
            if (tier > 0 && cSolution.boxByTier[tier - 1].Count > 0 && cData.boxColumn[cSolution.boxByTier[tier - 1][0]] == 0)
            {
                if (cSolution.getFeasibility(cSolution.boxByTier[tier - 1][0]))
                {
                    if (pinnedTier == tier)
                    {
                        //if it's going down the first time update pinned column
                        pinningCycle(tier - 1, 0, nrAssigned + 1, newColumn, pinnedTier, newColumn, false, dominated);
                        if (!tempNode.dominated && cSolution.checkPinningDominance(0, cSolution.boxByTier[tier - 1][0]))
                        {
                            tempNode.dominated = true;
                        }
                    }
                    else {
                        //if you went down several tiers already don't update pinned column
                        pinningCycle(tier - 1, 0, nrAssigned + 1, pinnedColumn, pinnedTier, newColumn, false, dominated);
                        if (!tempNode.dominated && cSolution.checkPinningDominance(0,cSolution.boxByTier[tier - 1][0]))
                        {
                            tempNode.dominated = true;
                        }
                    }
                    
                }
            }
            
        }

        public void killMe()
        {
            for (int i = 0; i < cData.num_Boxes + 1; i++) {
                lookUp[i].Clear();
                lookUp[i] = null;
            }
         
            lookUp = null;

            for (int i = 0; i < cData.num_Boxes; i++)
            {
                nodeList[i].Clear();
                nodeList[i] = null;
            }
            nodeList = null;
        }


 

        public List<List<int>> getOptSequence()
        {
            
            List<List<int>> sequence = new List<List<int>>();
            List<int> cycle;
            int index = 0;
            cNode actNode;
            cNode prevNode;

            IDictionaryEnumerator myEnum;
            myEnum = lookUp[cData.num_Boxes].GetEnumerator();
            myEnum.MoveNext();
            actNode = (cNode)myEnum.Value;

            



            
            while (actNode.bestPrev != null)
            {

                prevNode = actNode.bestPrev;
                cSolution.resetMe(prevNode);
                cycle = new List<int>();
                index++;

                for (int i = cSolution.maxHeight; i >= 0; i--)
                {
                    for(int j = 0; j < cSolution.boxByTier[i].Count;j++) {
                        if (actNode.assigned[cSolution.boxByTier[i][j]]) {
                            cycle.Add(cSolution.boxByTier[i][j]);
                        }
                        
                    }

                }
                sequence.Insert(0, cycle);

                actNode = actNode.bestPrev;
                
            }
            return sequence;
        }

        public int getObjective()
        {
         
            cNode actNode;
          
            IDictionaryEnumerator myEnum;
            myEnum = lookUp[cData.num_Boxes].GetEnumerator();
            myEnum.MoveNext();
            actNode = (cNode)myEnum.Value;

            return actNode.objVal;
        }


    }
}
