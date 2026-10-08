
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.Collections;

namespace Aulokomp
{
    class cSolution
    {
        public static cNode actNode;
        public static int maxHeight;
        public static int[] actBoxHeight;
        public static int[] retBoxes;
        public static List<int>[] boxByTier;

        public static void initMe()
        {
            killMe();

            boxByTier = new List<int>[cData.max_Height];
            actBoxHeight = new int[cData.num_Boxes];
            for (int i = 0; i < cData.max_Height; i++)
            {
                boxByTier[i] = new List<int>();
            }

        }


        public static void resetMe(cNode a)
        {
            for (int i = 0; i < cData.max_Height; i++)
            {
                boxByTier[i].Clear();
            }
            actNode = a;
            setBoxesByTier();
            calculateRetrieved();
        }


        public static void killMe()
        {
            actNode = null;
            retBoxes = null;
            actBoxHeight = null;

            if (boxByTier != null)
            {
                for (int i = 0; i < boxByTier.Length; i++)
                {
                    boxByTier[i].Clear();
                    boxByTier[i] = null;
                }
                boxByTier = null;
            }
        }

        private static void calculateRetrieved()
        {
            retBoxes = new int[cData.num_Columns];

            for (int i = 0; i < cData.num_Columns; i++)
            {
                for (int j = 0; j < cData.boxByColumn[i].Count; j++)
                {
                    if (actNode.assigned[cData.boxByColumn[i][j]])
                    {
                        retBoxes[i]++;
                    };
                }

            }
        }

        private static void setBoxesByTier()
        {
            int index = 0;
            for (int i = 0; i < cData.num_Columns; i++)
            {
                index = 0;
                for (int j = 0; j < cData.boxByColumn[i].Count; j++)
                {
                    if (actNode.assigned[cData.boxByColumn[i][j]])
                    {
                        index++;
                    }
                    else
                    {
                        boxByTier[cData.boxHeight[cData.boxByColumn[i][j]] - index].Add(cData.boxByColumn[i][j]);

                        actBoxHeight[cData.boxByColumn[i][j]] = cData.boxHeight[cData.boxByColumn[i][j]] - index;

                    }
                }
            }

            for (int i = cData.max_Height - 1; i >= 0; i--)
            {
                if (boxByTier[i].Count > 0)
                {
                    maxHeight = i;
                    break;
                }
            }

        }

        public static bool getAccessibility(int box)
        {
            // Can the box the accessed?

            for (int i = 0; i < cData.boxColumn[box]; i++)

            {

                if (cData.colHeight[i] - retBoxes[i] < actBoxHeight[box])
                {
                    return false;
                }

            }

            return true;
        }

        public static bool getFeasibility(int box)
        {
            int maxTier = actBoxHeight[box];
            int actTier = maxHeight;
            int index;
            int highBox;
            while (maxTier < actTier)
            {
                for (int i = 0; i < boxByTier[actTier].Count; i++) {
                    highBox = boxByTier[actTier][i];
                    if (cData.boxColumn[highBox] > cData.boxColumn[box])
                    {
                        index = 0;
                        for (int j = 0; j < cData.boxByColumn[cData.boxColumn[highBox]].Count; j++) {
                            if (cData.boxByColumn[cData.boxColumn[highBox]][j] == boxByTier[actTier][i])
                            {
                                break;
                            }
                            // there are boxes to be retrieved below the highbox
                            else if (!actNode.assigned[cData.boxByColumn[cData.boxColumn[highBox]][j]]) {
                                index++;
                            } 
                        }
                        if (maxTier < actBoxHeight[highBox] - index) {
                            maxTier = actBoxHeight[highBox] - index;
                        }
                        
                    }

                }
                actTier--;
            }
            
           

            if (cData.colHeight[cData.boxColumn[box]] - retBoxes[cData.boxColumn[box]] < maxTier) {
                return false;
            }

            return true;
        }
        
        public static int getObjective(int box, int pinnedColumn)
        {
            int obj;
            int index = 0;

            for (int i = 0; i < cData.boxByColumn[cData.boxColumn[box]].Count; i++)
            {
                if (cData.boxByColumn[cData.boxColumn[box]][i] == box)
                {
                    break;
                }
                else if (actNode.assigned[cData.boxByColumn[cData.boxColumn[box]][i]])
                {
                    index++;
                }
            }

            obj = cData.boxObj[box][pinnedColumn + 1][cData.boxObj[box][pinnedColumn + 1].Count - index - 1];

            for (int i = pinnedColumn + 1; i < cData.boxColumn[box]; i++)
            {
                obj -= retBoxes[i];

            }

            for (int i = cData.boxByColumn[cData.boxColumn[box]].Count - 1; i > 0; i--)
            {
                if (cData.boxByColumn[cData.boxColumn[box]][i] == box)
                {
                    break;
                }
                else if (actNode.assigned[cData.boxByColumn[cData.boxColumn[box]][i]])
                {
                    obj--;
                }

            }

            return obj;
        }


        //get current height of a box
        public static int getHeight(int box)
        {
            //determine box height
            int height;

            height = cData.boxHeight[box];
            for (int i = 0; i < cData.boxByColumn[cData.boxColumn[box]].Count; i++)
            {
                if (cData.boxByColumn[cData.boxColumn[box]][i] == box)
                {
                    break;
                }

                else if (actNode.assigned[cData.boxByColumn[cData.boxColumn[box]][i]])
                {
                    height--;
                }
            }
            return height;
        }
        //Find out whether a column has box on a given height and return it (otherwise return -1)
        public static int getBoxAtHeight(int height, int column)
        {
            int index;

            //find box on the same height
            index = 0;
            for (int i = 0; i < cData.boxByColumn[column].Count; i++)
            {
                if (actNode.assigned[cData.boxByColumn[column][i]])
                {
                    index++;
                }
                else if (height == cData.boxHeight[cData.boxByColumn[column][i]] - index)
                {
                    return cData.boxByColumn[column][i];
                }
                else if (height < cData.boxHeight[cData.boxByColumn[column][i]] - index)
                {
                    break;
                }
            }


            return -1;
        }


        // checks whether there is an accessible box on top of this one that should be picked instead
        public static bool checkOnTopDominance(int box)
        {
            int topBox;
            int index;
 
           
            index = cData.boxByColumn[cData.boxColumn[box]].IndexOf(box) + 1;

            while (index < cData.boxByColumn[cData.boxColumn[box]].Count)
            {
                topBox = cData.boxByColumn[cData.boxColumn[box]][index];

                //FIXME: what if more than one box is stacked on top of each other
                if (!actNode.assigned[topBox])
                {
                    //Is there a box stacked right on top of this box that is unassigned and accessible?
                    if (actBoxHeight[topBox] == actBoxHeight[box] + 1 && getAccessibility(topBox))
                    {
                        return true;
                    }
                    //else break while loop
                    break;
                }
                else { index++; }

            }

            return false;
        }

        // checks whether there is a single box in a column that is to the left and on top of all other boxes
        //if there is such a box, return it; otherwise, return -1

        public static int getLeftTopDominance()
        {
            int box = -1;


            //FIXME: is it necessary to be the only one 
            if (boxByTier[maxHeight].Count != 1)
            {
                return -1;
            }
            box = boxByTier[maxHeight][0];

            for (int i = 0; i < maxHeight; i++)
            {
                if (boxByTier[i].Count > 0)
                {
                    //FIXME: <= must be correct!?
                    if (cData.boxColumn[boxByTier[i][0]] <= cData.boxColumn[box])
                    {
                        return -1;
                    }
                }

            }



            return box;
        }

        public static bool checkPinningDominance(int lastCol, int box)
        {
            int col;
  
  
            int tier;
           
            col = cData.boxColumn[box];

            // is it the only box left in the column
            if (cData.boxByColumn[col].Count - retBoxes[col] == 1)
            {
                //are there any boxes in between this column and the last picked column then return false
                for (int i = lastCol+1; i < col; i++)
                {

                    if (cData.boxByColumn[i].Count - retBoxes[i] != 0)
                    {
                        return false ;
                    }

                }

                // what is the highest tier that needs to be accessed to the right of this box
                for (tier = maxHeight; tier > actBoxHeight[box]; tier--)
                {

                    if (boxByTier[tier].Count >=1 && cData.boxColumn[boxByTier[tier][boxByTier[tier].Count - 1]] > cData.boxColumn[box])
                    {
                        break;
                    }

                }
                // does removing the box not threaten accessibility of other boxes
                if (cData.colHeight[cData.boxColumn[box]] - retBoxes[cData.boxColumn[box]] >= tier)
                {
                    return true;
                }
            }

            return false;
        }

        public static void printActInstance()
        {
            Debug.WriteLine("");
            for (int i = cData.max_Height; i > 0; i--)
            {
                for (int j = 0; j < cData.num_Columns; j++)
                {

                    if (cData.colHeight[j] - retBoxes[j] < i)
                    {
                        Debug.Write(" ");
                    }
                    else
                    {
                        int box = -1;
                        for (int k = 0; k < cData.boxByColumn[j].Count; k++)
                        {
                            if (!actNode.assigned[cData.boxByColumn[j][k]] && actBoxHeight[cData.boxByColumn[j][k]] == i - 1)
                            {
                                box = cData.boxByColumn[j][k];
                                break;
                            }
                        }
                        if (box != -1)
                        {
                            Debug.Write(box);
                        }
                        else
                        {
                            Debug.Write("-");
                        }
                    }
                }
                Debug.WriteLine("");




            }

        }

        public static void printActSequence()
        {

            List<List<int>> sequence = new List<List<int>>();
            List<int> cycle;
            int index = 0;
            cNode tempNode;
            cNode prevNode;

            tempNode = actNode;


            while (tempNode.bestPrev != null)
            {

                prevNode = tempNode.bestPrev;
                cSolution.resetMe(prevNode);
                cycle = new List<int>();
                index++;

                for (int i = cSolution.maxHeight; i >= 0; i--)
                {
                    for (int j = 0; j < cSolution.boxByTier[i].Count; j++)
                    {
                        if (tempNode.assigned[cSolution.boxByTier[i][j]])
                        {
                            cycle.Add(cSolution.boxByTier[i][j]);
                        }

                    }

                }
                sequence.Insert(0, cycle);

                tempNode = tempNode.bestPrev;

            }
            Debug.WriteLine("");

            for (int i = 0; i < sequence.Count; i++)
            {
                Debug.Write("(");
                for (int j = 0; j < sequence[i].Count - 1; j++)
                {
                    Debug.Write(sequence[i][j] + "->");
                }
                Debug.Write(sequence[i][sequence[i].Count - 1]);
                Debug.Write(")");
            }

            Debug.WriteLine("");

        }


        public static void printObjective()
        {
            Debug.WriteLine("");
            Debug.Write(actNode.objVal.ToString());
            Debug.WriteLine("");
        }
    }
}