using System;
using System.Diagnostics;
using System.Collections.Generic;

namespace Aulokomp
{
    class Program
    {
        static void Main(string[] args)
        {
            List<List<int>> optSequence;

            Random rng = new Random(1); //  Fixed Seed Ranomizer

            int[] numColumns = { 20, 24, 28 };
            int[] maxHeight = { 20, 24, 28 };
            int[] numBoxes = { 18, 21, 24 };
            double[] occupancy = { 0.5, 0.75, 1.0 };
            int instance = 0;
            //for (int i = 0; i < numBoxes.Length; i++)
            //{
            //    for (int j = 0; j < maxHeight.Length; j++)
            //    {
            //        for (int k = 0; k < numColumns.Length; k++)
            //        {
            //            for (int l = 0; l < occupancy.Length; l++)
            //            {
            //                for (int m = 0; m < 10; m++)
            //                {

            //                    cData.initMe(rng);
            //                    instance++;
            //                    cData.instanceNr = instance;
            //                    cData.max_Height = maxHeight[j];
            //                    cData.num_Columns = numColumns[k];
            //                    cData.num_Boxes = numBoxes[i];
            //                    cData.occupancy = occupancy[l];
            //                    cData.randomizeHeights();
            //                    cData.randomizeBoxes();

            //                    cData.writeInstanceToFile();
            //                    cData.killMe();
            //                }

            //            }
            //        }
            //    }
            //}

            for (int large= 0; large < 2; large++)
            {
                for (instance = 0; instance < 810; instance++)
                {

                    cData.readInstancefromFile(instance + 1,large);
                    printInstance();

                    cDP dp = new cDP(600);
                    if (dp.solveDP())
                    {

                        optSequence = dp.getOptSequence();

                        if (large == 0)
                        {
                            cData.writeResults("Results.txt", instance + 1, dp.getObjective(), dp.stateCounter, dp.watch.Elapsed.TotalSeconds);


                        }
                        else {
                            cData.writeResults("Results_large.txt", instance + 1, dp.getObjective(), dp.stateCounter, dp.watch.Elapsed.TotalSeconds);
                        }
                        





                        Debug.WriteLine("");

                        for (int i = 0; i < optSequence.Count; i++)
                        {
                            Debug.Write("(");
                            for (int j = 0; j < optSequence[i].Count - 1; j++)
                            {
                                Debug.Write(optSequence[i][j] + "->");
                            }
                            Debug.Write(optSequence[i][optSequence[i].Count - 1]);
                            Debug.Write(")");
                        }

                        Debug.WriteLine("");
                        Debug.WriteLine("Obj: " + dp.getObjective());
                    }
                    else
                    {
                        if (large == 0)
                        {
                            cData.writeResults("Results.txt", instance + 1, -1, dp.stateCounter, dp.watch.Elapsed.TotalSeconds);


                        }
                        else
                        {
                            cData.writeResults("Results_large.txt", instance + 1, -1, dp.stateCounter, dp.watch.Elapsed.TotalSeconds);
                        }
                     }

                    cData.killMe();
                }


            }

        }
        public static void printInstance()
        {
            for (int i = cData.max_Height; i > 0; i--)
            {
                for (int j = 0; j < cData.num_Columns; j++)
                {

                    if (cData.colHeight[j] < i)
                    {
                        Debug.Write(" ");
                    }
                    else
                    {
                        int box = -1;
                        for (int k = 0; k < cData.boxByColumn[j].Count; k++)
                        {
                            if (cData.boxHeight[cData.boxByColumn[j][k]] == i - 1)
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
    }
}
